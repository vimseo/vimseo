# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import annotations

import contextlib
from collections import defaultdict
from typing import TYPE_CHECKING

from vimseo.utilities.distribution import DistributionParameters
from vimseo.utilities.distribution import InterfacedDistributionSettings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from gemseo.algos.design_space import DesignSpace
    from gemseo.algos.parameter_space import ParameterSpace

OPTIONS_PER_DISTRIBUTION = {
    "OTUniformDistribution": ("lower", "upper"),
    "OTNormalDistribution": ("mu", "sigma"),
    "OTTriangularDistribution": ("lower", "upper", "mode"),
    "OTWeibullDistribution": ("location", "scale", "shape"),
    "OTExponentialDistribution": ("loc", "rate"),
    "SPUniformDistribution": ("lower", "upper"),
    "SPNormalDistribution": ("mu", "sigma"),
    "SPTriangularDistribution": ("lower", "upper", "mode"),
}

# Stock gemseo's per-distribution settings classes use their own field names for
# some parameters (e.g. ``minimum``/``maximum`` instead of vimseo's generic
# ``lower``/``upper``). Only the names that differ need an entry here.
_NATIVE_FIELD_NAMES = {
    "lower": "minimum",
    "upper": "maximum",
}

# gemseo's ``OTWeibullDistribution`` always builds a WeibullMin (or
# WeibullMax) OpenTURNS distribution under the hood, and
# ``add_random_variable_interface`` canonicalizes the attached settings'
# ``name`` to match (so it round-trips correctly through serialization) --
# but "OTWeibullMinDistribution"/"OTWeibullMaxDistribution" are not
# registrable gemseo distribution classes, only "OTWeibullDistribution" is.
# Map the canonicalized name back when (re)constructing a distribution.
_CANONICAL_TO_CONSTRUCTIBLE_NAME = {
    "WeibullMin": "Weibull",
    "WeibullMax": "Weibull",
}


def _to_native_parameters(
    distribution_name: str, settings: DistributionParameters
) -> dict:
    """Convert vimseo's generic distribution settings to gemseo's native kwargs."""
    dumped = settings.model_dump()
    parameters = {
        _NATIVE_FIELD_NAMES.get(name, name): dumped[name]
        for name in OPTIONS_PER_DISTRIBUTION[distribution_name]
    }
    for bound in ("lower_bound", "upper_bound"):
        if dumped.get(bound) is not None:
            parameters[bound] = dumped[bound]
    return parameters


def _attach_settings(
    parameter_space: ParameterSpace,
    variable_name: str,
    settings: DistributionParameters | InterfacedDistributionSettings,
) -> None:
    """Keep the vimseo settings alongside each marginal of the built variable.

    Stock gemseo distribution objects no longer expose the settings they were
    built from (unlike the private fork this used to rely on), so vimseo
    attaches them itself in order to be able to serialize them back later
    (see :class:`~.SpaceToolFileIO`). For a vector variable, each marginal gets
    its own component of any per-component (list-valued) field, matching the
    per-marginal settings the fork used to expose.
    """
    marginals = parameter_space.distributions[variable_name].marginals
    dumped = settings.model_dump()
    for index, marginal in enumerate(marginals):
        component_values = {
            name: value[index] if isinstance(value, list) else value
            for name, value in dumped.items()
        }
        marginal.vimseo_settings = type(settings)(**component_values)


def add_random_variable_interface(
    parameter_space: ParameterSpace,
    variable_name: str,
    settings: DistributionParameters | InterfacedDistributionSettings,
    size: int = 1,
):
    """An interface to handle seamlessly the interfaces to
    :meth:`gemseo.algos.parameter_space.add_random_variable` for an OT distribution."""
    if isinstance(settings, InterfacedDistributionSettings):
        if size != 1:
            msg = (
                f"Only scalars are handled for an "
                f"``InterfaceDistribution``. But variable {variable_name} "
                f"has dimension {size}."
            )
            raise ValueError(msg)
        parameter_space.add_random_variable(
            variable_name,
            "OTDistribution",
            size=size,
            interfaced_distribution=settings.name,
            interfaced_distribution_parameters=settings.parameters,
            lower_bound=settings.lower_bound,
            upper_bound=settings.upper_bound,
        )
    else:
        # ``settings.name`` may already be the canonicalized "WeibullMin"/
        # "WeibullMax" (see below) when re-building a space from settings
        # that were previously attached/serialized: gemseo only registers
        # "OTWeibullDistribution", not "OTWeibullMinDistribution", so the
        # canonical name must be mapped back for construction.
        constructible_name = _CANONICAL_TO_CONSTRUCTIBLE_NAME.get(
            settings.name, settings.name
        )
        distribution_name = f"OT{constructible_name}Distribution"
        parameters = _to_native_parameters(distribution_name, settings)
        if size == 1:
            parameter_space.add_random_variable(
                variable_name,
                distribution_name,
                size=size,
                **parameters,
            )
        else:
            parameter_space.add_random_vector(
                variable_name,
                size=size,
                distribution=distribution_name,
                **parameters,
            )
        if settings.name == "Weibull":
            # gemseo's ``OTWeibullDistribution`` always builds a WeibullMin (or
            # WeibullMax) OpenTURNS distribution under the hood; canonicalize the
            # attached name to match, as vimseo's own serialization/tests expect.
            settings = settings.model_copy(update={"name": "WeibullMin"})

    _attach_settings(parameter_space, variable_name, settings)


def distribution_to_dict(variable_name: str, distribution) -> dict:
    """Return one uncertain variable of a parameter space as a plain dict.

    The per-marginal ``vimseo_settings`` (see :func:`_attach_settings`) are
    recomposed into a single, possibly vector-valued, JSON/HDF5-safe dict of
    primitives -- the inverse of what :func:`add_random_variable_interface`
    does when building the space.

    Args:
        variable_name: The name of the variable (used only for the error
            message below).
        distribution: ``parameter_space.distributions[variable_name]``.

    Raises:
        AttributeError: If a marginal was not built through
            :func:`add_random_variable_interface` and so carries no
            ``vimseo_settings``.
        ValueError: If the variable uses the ``InterfacedDistribution``
            interface and has a dimension greater than 1 (not handled).
    """
    entry = defaultdict(list)
    for marginal in distribution.marginals:
        settings = marginal.vimseo_settings.model_dump()
        ot_distribution_name = f"OT{settings['name']}Distribution"
        expected_keys = OPTIONS_PER_DISTRIBUTION.get(ot_distribution_name, ())
        if expected_keys == () or not set(expected_keys).issubset(set(settings.keys())):
            if distribution.dimension > 1:
                msg = (
                    f"Distribution {marginal} has the "
                    f"``InterfacedDistribution`` interface, and has dimension "
                    f"{distribution.dimension}. Only scalar variable is handled."
                )
                raise ValueError(msg)
            # distribution interface is with parameters. We only handle
            # scalar variables in this case:
            entry = settings
        else:
            for k in expected_keys:
                if distribution.dimension == 1:
                    entry[k] = settings[k]
                else:
                    entry[k].append(settings[k])
            entry["name"] = settings["name"]
            # Truncation bounds are cross-cutting: not part of
            # OPTIONS_PER_DISTRIBUTION, forwarded separately here and in
            # add_random_variable_interface so a truncated distribution
            # round-trips.
            for bound in ("lower_bound", "upper_bound"):
                value = settings.get(bound)
                if value is None:
                    continue
                if distribution.dimension == 1:
                    entry[bound] = value
                else:
                    entry[bound].append(value)
    entry["size"] = distribution.dimension
    return entry


def distributions_to_dict(parameter_space: ParameterSpace) -> dict:
    """Return the uncertain variables of a parameter space as a plain dict.

    Applies :func:`distribution_to_dict` to every uncertain variable. This is
    the format historically produced by
    :class:`~vimseo.io.space_io.SpaceToolFileIO` for its (deprecated) JSON
    export; moved here so both the JSON export and the HDF5 tool-result
    serializer share the same, tested, logic.

    Raises:
        AttributeError: See :func:`distribution_to_dict`.
        ValueError: See :func:`distribution_to_dict`.
    """
    return {
        variable_name: distribution_to_dict(variable_name, distribution)
        for variable_name, distribution in parameter_space.distributions.items()
    }


def add_distributions_from_dict(
    parameter_space: ParameterSpace, data: Mapping[str, Mapping]
) -> None:
    """Add uncertain variables to a parameter space from a dict.

    The dict must have the shape produced by :func:`distributions_to_dict`.
    Mutates ``parameter_space`` in place.
    """
    for variable_name, raw_options in data.items():
        # Copy: `size` is popped below, and the caller's dict should not be
        # mutated (it may be reused, e.g. by a test).
        options = dict(raw_options)
        # TODO bad design: the kind of distribution interface is inferred
        #  from the option keys.
        size = options.pop("size")
        if "parameters" in options and len(options["parameters"]) > 0:
            if size > 1:
                msg = "Vector is not handled."
                raise ValueError(msg)
            settings = InterfacedDistributionSettings(
                name=options["name"], parameters=tuple(options["parameters"])
            )
        else:
            settings = DistributionParameters(**options)
        add_random_variable_interface(
            parameter_space,
            variable_name,
            size=size,
            settings=settings,
        )


def deterministic_to_dict(space: DesignSpace) -> dict:
    """Return the deterministic variables of a design space as a plain dict.

    For a :class:`~gemseo.algos.parameter_space.ParameterSpace`, its
    uncertain variables (see :attr:`.ParameterSpace.uncertain_variables`)
    are excluded; a plain :class:`~gemseo.algos.design_space.DesignSpace`
    has none, so every variable is included.
    """
    uncertain_names = set(getattr(space, "uncertain_variables", ()))
    data = {}
    for name in space.variable_names:
        if name in uncertain_names:
            continue
        entry = {
            "size": space.get_size(name),
            "type": space.get_type(name),
            "lower_bound": space.get_lower_bound(name),
            "upper_bound": space.get_upper_bound(name),
        }
        with contextlib.suppress(KeyError):
            # KeyError: this variable has no current value.
            entry["value"] = space.get_current_value([name])
        data[name] = entry
    return data


def add_deterministic_from_dict(
    space: DesignSpace, data: Mapping[str, Mapping]
) -> None:
    """Add deterministic variables to a design space from a dict.

    The dict must have the shape produced by :func:`deterministic_to_dict`.
    Mutates ``space`` in place.
    """
    for name, entry in data.items():
        space.add_variable(
            name,
            size=int(entry["size"]),
            type_=entry["type"],
            lower_bound=entry["lower_bound"],
            upper_bound=entry["upper_bound"],
            value=entry.get("value"),
        )
