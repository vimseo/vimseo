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

"""Describe an OpenTURNS distribution in clear, and build it back.

An OpenTURNS distribution is described by plain data:

- a univariate distribution by its class name and its parameters
  (:class:`.InterfacedDistributionSettings`),
- a truncated distribution by the description of the truncated distribution and its
  bounds,
- a joint distribution by the descriptions of its marginals and of its copula.

The other distributions, e.g. a ``UserDefined`` or a ``DeconditionedDistribution``
distribution, are not described: :func:`ot_distribution_to_dict` raises a
``ValueError``.
"""

from __future__ import annotations

from typing import Any

import openturns as ot
from numpy import allclose
from numpy import array

from vimseo.utilities.distribution import InterfacedDistributionSettings

_JOINT_DISTRIBUTION_NAMES = ("ComposedDistribution", "JointDistribution")
"""The names of the OpenTURNS classes of the joint distributions."""

_TRUNCATED_DISTRIBUTION_NAME = "TruncatedDistribution"
"""The name of the OpenTURNS class of the truncated distributions."""


def is_ot_distribution(value: Any) -> bool:
    """Whether a value is an OpenTURNS distribution.

    Args:
        value: The value.
    """
    return isinstance(value, (ot.Distribution, ot.DistributionImplementation))


def get_class_name(distribution: ot.Distribution) -> str:
    """Return the name of the class of an OpenTURNS distribution.

    The marginals or the copula of a distribution are returned by OpenTURNS as a
    generic ``Distribution`` wrapping the actual distribution.

    Args:
        distribution: The distribution.
    """
    if hasattr(distribution, "getImplementation"):
        return distribution.getImplementation().getClassName()
    return distribution.getClassName()


def _describe(distribution: ot.Distribution) -> dict[str, Any]:
    """Describe a distribution in clear, without checking the description."""
    name = get_class_name(distribution)

    if name in _JOINT_DISTRIBUTION_NAMES:
        copula = distribution.getCopula()
        return {
            "kind": "joint",
            "name": name,
            "marginals": [
                _describe(distribution.getMarginal(i))
                for i in range(distribution.getDimension())
            ],
            "copula": {
                "name": get_class_name(copula),
                "dimension": copula.getDimension(),
                "parameters": tuple(copula.getParameter()),
            },
        }

    if name == _TRUNCATED_DISTRIBUTION_NAME:
        bounds = distribution.getBounds()
        return {
            "kind": "truncated",
            "distribution": _describe(distribution.getDistribution()),
            "lower_bound": tuple(bounds.getLowerBound()),
            "upper_bound": tuple(bounds.getUpperBound()),
            "finite_lower_bound": tuple(bool(b) for b in bounds.getFiniteLowerBound()),
            "finite_upper_bound": tuple(bool(b) for b in bounds.getFiniteUpperBound()),
        }

    if distribution.getDimension() == 1:
        return {
            "kind": "univariate",
            "settings": InterfacedDistributionSettings(
                name=name, parameters=tuple(distribution.getParameter())
            ),
        }

    msg = f"The OpenTURNS distribution {name} cannot be described in clear."
    raise ValueError(msg)


def ot_distribution_from_dict(data: dict[str, Any]) -> ot.Distribution:
    """Build an OpenTURNS distribution from its description.

    Args:
        data: The description of the distribution,
            as returned by :func:`ot_distribution_to_dict`.

    Returns:
        The distribution.
    """
    kind = data["kind"]

    if kind == "joint":
        copula_data = data["copula"]
        # The values read from an HDF5 file are NumPy scalars, that the OpenTURNS
        # constructors reject.
        copula = getattr(ot, copula_data["name"])(int(copula_data["dimension"]))
        if len(copula_data["parameters"]):
            copula.setParameter([float(p) for p in copula_data["parameters"]])
        marginals = [ot_distribution_from_dict(m) for m in data["marginals"]]
        return getattr(ot, data["name"])(marginals, copula)

    if kind == "truncated":
        interval = ot.Interval(
            [float(b) for b in data["lower_bound"]],
            [float(b) for b in data["upper_bound"]],
            [bool(b) for b in data["finite_lower_bound"]],
            [bool(b) for b in data["finite_upper_bound"]],
        )
        return ot.TruncatedDistribution(
            ot_distribution_from_dict(data["distribution"]), interval
        )

    settings = data["settings"]
    if not isinstance(settings, InterfacedDistributionSettings):
        settings = InterfacedDistributionSettings(**settings)
    distribution = getattr(ot, settings.name)()
    distribution.setParameter([float(p) for p in settings.parameters])
    return distribution


def ot_distribution_to_dict(distribution: ot.Distribution) -> dict[str, Any]:
    """Describe an OpenTURNS distribution in clear.

    The description is checked by building the distribution back from it.

    Args:
        distribution: The distribution.

    Returns:
        The description of the distribution.

    Raises:
        ValueError: If the distribution cannot be described in clear,
            or if the distribution built from its description differs.
    """
    try:
        description = _describe(distribution)
        rebuilt = ot_distribution_from_dict(description)
    except Exception as error:  # ruff: ignore[blind-except]
        # OpenTURNS raises various exceptions for the unsupported distributions.
        msg = (
            f"The OpenTURNS distribution {get_class_name(distribution)} "
            f"cannot be described in clear: {error}"
        )
        raise ValueError(msg) from error

    parameters = array(distribution.getParameter())
    rebuilt_parameters = array(rebuilt.getParameter())
    if (
        get_class_name(rebuilt) != get_class_name(distribution)
        or rebuilt.getDimension() != distribution.getDimension()
        or parameters.shape != rebuilt_parameters.shape
        or not allclose(parameters, rebuilt_parameters)
    ):
        msg = (
            f"The OpenTURNS distribution {distribution} cannot be described in "
            f"clear: it is built back as {rebuilt}."
        )
        raise ValueError(msg)

    return description
