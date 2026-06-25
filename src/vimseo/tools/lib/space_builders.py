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

# Copyright (c) 2022 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Ludovic BARRIERE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

import abc
import inspect
import logging
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from gemseo.uncertainty.distributions.base_distribution import DistributionSettings
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import inf
from numpy import sign
from sympy.parsing.sympy_parser import parse_expr

from vimseo.config.global_configuration import _configuration as config
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.space.random_variable_interface import OPTIONS_PER_DISTRIBUTION
from vimseo.tools.space.random_variable_interface import add_random_variable_interface

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

    from gemseo.algos.parameter_space import ParameterSpace

    from vimseo.core.base_integrated_model import IntegratedModel

LOGGER = logging.getLogger(__name__)


class SpaceBuilder(BaseTool):
    """A base class to derive builders of parameter spaces.

    The builders construct a :class:`.ParameterSpace` with a pre-defined method.
    """

    _OPTIONS_PER_DISTRIBUTION: ClassVar[Mapping[str, Any]] = OPTIONS_PER_DISTRIBUTION
    """The options that must be passed to :meth:`ParameterSpace.add_random_variable` to
    build the corresponding distribution.

    It allows to select the appropriate options to make the builder compatible with
    several type of distribution, thus avoiding to define one builder per distribution
    type.
    """

    _AVAILABLE_DISTRIBUTIONS: ClassVar[Iterable[str]] = (
        "OTUniformDistribution",
        "OTTriangularDistribution",
        "OTNormalDistribution",
    )
    """The available distributions."""

    _IS_JSON_GRAMMAR = True

    DEFAULT_CENTER_EXPRESSION = "0.5*(mini+maxi)"
    """Symbolic expression for the central value of the distribution, taking 'mini' and
    'maxi' as parameters."""

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )

    @property
    def grammar_names(self):
        """The names of the grammar.

        For builder ``FromCenterAndCov``, due to the fact that variables
        ``minimum_values`` and ``maximum_values`` can be ``None`` or a dict,
        these variables are not validated by the grammar.
        So we manually add these variable names.
        """
        if self.__class__.__name__ == "FromCenterAndCov":
            return [*list(self.grammar.names), "lower_bounds", "upper_bounds"]
        return list(self.grammar.names)

    @classmethod
    def _check_input_dimension(cls, model, input_names):
        for name in input_names:
            value = model.default_input_data[name]
            if value.ndim != 1:
                msg = f"Input variable {name} must be of dimension one."
                raise ValueError(msg)
            if value.shape[0] != 1:
                LOGGER.warning(f"Input variable {name} is a vector.")

    def _is_distribution_available(self, distribution_name):
        if distribution_name not in self._AVAILABLE_DISTRIBUTIONS:
            msg = (
                f"Distribution name {distribution_name} must be in "
                f"{self._AVAILABLE_DISTRIBUTIONS}"
            )
            raise ValueError(msg)

    def _eval_center_expr(self, string_expr, min_value, max_value):
        return float(
            parse_expr(string_expr).evalf(subs={"mini": min_value, "maxi": max_value})
        )

    @abc.abstractmethod
    def build(
        self,
        parameter_space: ParameterSpace,
        distribution_name: str,
        model: IntegratedModel = None,
        **options,
    ) -> None:
        """Update a space of parameters.

        Args:
            parameter_space: The :class:`~.ParameterSpace` to update.
            distribution_name: The name of the distribution.
            model: An :class:`~.IntegratedModel`.
        """

    def get_builder_options(self):
        return inspect.signature(self.build)

    def get_available_distributions(self):
        return self._AVAILABLE_DISTRIBUTIONS

    # TODO remove this method
    @classmethod
    def filter_options(cls, distribution_name: str, **options):
        """Filter options to obtain an options compatible with the distribution to
        compute. Add a variable to the space.

        Args:
           distribution_name: The name of the distribution of the updated variable.
        """
        filtered_options = {}
        for option_name in cls._OPTIONS_PER_DISTRIBUTION[distribution_name] + (
            "lower_bound",
            "upper_bound",
        ):
            if option_name in options:
                filtered_options[option_name] = options[option_name]
        return filtered_options

    def _filter_options_and_add_variable(
        self, parameter_space, name, distribution_name, **options
    ):
        """Filters options to obtain an options compatible with the distribution to
        compute. Add a variable to the space.

        Args:
           parameter_space: A parameter space to update.
           name: The name of variable to update.
           distribution_name: The name of the distribution of the updated variable.
        """

        if name in parameter_space.variable_names:
            parameter_space.remove_variable(name)

        settings = DistributionSettings(
            name=distribution_name[2:-12],
            **self.filter_options(distribution_name, **options),
        )

        add_random_variable_interface(
            parameter_space,
            variable_name=name,
            settings=settings,
            size=options["size"],
        )


class FromMinAndMax(SpaceBuilder):
    """A space builder which computes distributions based on a minimum and a maximum
    value."""

    _AVAILABLE_DISTRIBUTIONS = (
        "OTUniformDistribution",
        "OTTriangularDistribution",
    )

    def _compute_full_options(self, center, minimum, maximum):
        """Compute the full distribution options."""

        return {
            "mu": None,
            "sigma": None,
            "lower": minimum,
            "upper": maximum,
            "mode": center,
        }

    def build(
        self,
        parameter_space,
        distribution_name,
        model=None,
        minimum_values: Mapping[str, float] | None = None,
        maximum_values: Mapping[str, float] | None = None,
        center_value_expr: str = "",
        size: int = 1,
    ) -> None:
        """Updates the space of parameters.

        Args:
            minimum_values: A dictionary where keys are the parameter names
                and values the minimum values of the distribution.
            maximum_values: A dictionary where keys are the parameter names
                and values the maximum values of the distribution.
            center_value_expr: A dictionary where keys are the parameter names
                and values the central value of the distribution.
        """

        self._is_distribution_available(distribution_name)

        center_value_expr = (
            self.DEFAULT_CENTER_EXPRESSION
            if center_value_expr == ""
            else center_value_expr
        )

        minimum_values = {} if minimum_values is None else minimum_values
        maximum_values = {} if maximum_values is None else maximum_values

        if set(minimum_values.keys()) != set(maximum_values.keys()):
            msg = (
                f"Variable names for minimum {minimum_values.keys()} "
                f"and maximum {maximum_values.keys()} must be the same."
            )
            raise ValueError(msg)

        for name in minimum_values:
            minimum = minimum_values[name]
            maximum = maximum_values[name]
            center = self._eval_center_expr(center_value_expr, minimum, maximum)

            full_options = self._compute_full_options(
                center, minimum_values[name], maximum_values[name]
            )

            self._filter_options_and_add_variable(
                parameter_space, name, distribution_name, size=size, **full_options
            )


class FromModelMinAndMax(FromMinAndMax):
    """A space builder which computes distributions based on the minimum and maximum
    values of a model input variables."""

    _AVAILABLE_DISTRIBUTIONS = (
        "OTUniformDistribution",
        "OTTriangularDistribution",
    )

    def build(
        self,
        parameter_space,
        distribution_name,
        model,
        variable_names=(),
        use_default_values_as_center=False,
        center_value_expr: str = "",
    ) -> None:
        """Updates the space of parameter based on an :class:`~.IntegratedModel`.

        Args:
            variable_names: The parameters to keep among the model inputs. Note that
            by default the variables retained to be added to the parameter space
            are the intersection between the :attr:`model.lower_bounds.keys()` and
            :attr:`model.upper_bounds.keys()`.
            use_default_values_as_center: Whether to use the model default values as
                central value of the distributions. If left to ``False``,
                the half sum of the :attr:`~.IntegratedModel.lower_bounds` and
                :attr:`~.IntegratedModel.upper_bounds` of the model is used as
                the central value.
        """

        self._is_distribution_available(distribution_name)

        input_names = set(
            set(model.lower_bounds.keys()) & set(model.upper_bounds.keys())
        )
        if not set(variable_names).issubset(input_names):
            msg = (
                f"Some variables among {variable_names} are not model inputs, or have no "
                f"lower and upper bounds."
            )
            raise ValueError(msg)
        input_names = set(input_names & set(variable_names))

        self._check_input_dimension(model, input_names)

        # Reorder input_names according to model.default_input_data to ensure deterministic
        # order:
        reordered_input_names = [
            name for name in model.default_input_data if name in input_names
        ]

        center_value_expr = (
            self.DEFAULT_CENTER_EXPRESSION
            if center_value_expr == ""
            else center_value_expr
        )
        minimum_values = model.lower_bounds
        maximum_values = model.upper_bounds

        for name in reordered_input_names:
            minimum = minimum_values.get(name, -inf)
            maximum = maximum_values.get(name, inf)

            if use_default_values_as_center:
                center = model.default_input_data[name].item()
            else:
                center = self._eval_center_expr(center_value_expr, minimum, maximum)

            full_options = self._compute_full_options(
                center, minimum_values[name], maximum_values[name]
            )

            size = len(model.default_input_data[name])
            self._filter_options_and_add_variable(
                parameter_space, name, distribution_name, size=size, **full_options
            )


class FromCenterAndCov(SpaceBuilder):
    """A space builder which computes distributions from a center and a coefficient of
    variation around the center."""

    def _compute_full_options(
        self, center, cov, name, minimum=None, maximum=None, lb=None, ub=None
    ):
        """Compute the full distribution options."""

        if name == "OTNormalDistribution":
            return {
                "mu": center,
                "sigma": abs(cov * center),
                "lower_bound": lb,
                "upper_bound": ub,
            }
        return {
            "mu": center,
            "sigma": abs(cov * center),
            "lower": minimum,
            "upper": maximum,
            "mode": center,
            "lower_bound": max(lb, minimum) if lb is not None else None,
            "upper_bound": min(ub, maximum) if ub is not None else None,
        }

    def get_filtered_options(self, **options):
        names = [
            "parameter_space",
            "distribution_name",
            "model",
            "center_values",
            "cov",
            "lower_bounds",
            "upper_bounds",
        ]
        return {name: option for name, option in options.items() if name in names}

    def build(
        self,
        parameter_space,
        distribution_name,
        model=None,
        center_values: Mapping[str, float] | None = None,
        cov=0.05,
        lower_bounds: Mapping[str, float | None] | None = None,
        upper_bounds: Mapping[str, float | None] | None = None,
        size: int = 1,
    ) -> None:
        """Updates the space of parameters.

        Args:
            center_values: A dictionary where keys are the parameter names
                and values the central value of the distribution.
            cov: the coefficient of variation around the center used to define the
                minimum and maximum values of the distribution.
            lower_bounds: A dictionary where keys are the parameter names
                and values the lower bound of the distribution.
            upper_bounds: A dictionary where keys are the parameter names
                and values the upper bound of the distribution.
        """

        self._is_distribution_available(distribution_name)

        center_values = {} if center_values is None else center_values

        for name, center in center_values.items():
            if lower_bounds is None or name not in lower_bounds:
                lb = None
            else:
                lb = lower_bounds[name] or None
            if upper_bounds is None or name not in upper_bounds:
                ub = None
            else:
                ub = upper_bounds[name] or None
            full_options = self._compute_full_options(
                center,
                cov,
                distribution_name,
                center * (1 - sign(center) * cov),
                center * (1 + sign(center) * cov),
                lb=lb,
                ub=ub,
            )

            self._filter_options_and_add_variable(
                parameter_space, name, distribution_name, size=size, **full_options
            )


class FromModelCenterAndCov(FromCenterAndCov):
    """A space builder which computes distributions based on the minimum and maximum
    values of a model input variables."""

    def get_filtered_options(self, **options):
        names = [
            "parameter_space",
            "distribution_name",
            "model",
            "variable_names",
            "use_default_values_as_center",
            "center_value_expr",
            "cov",
            "truncate_to_model_bounds",
        ]
        return {name: option for name, option in options.items() if name in names}

    def build(
        self,
        parameter_space,
        distribution_name,
        model,
        variable_names=(),
        use_default_values_as_center=True,
        center_value_expr: str = "",
        cov=0.05,
        truncate_to_model_bounds: bool = True,
    ) -> None:
        """Updates the space of parameter based on an :class:`~.IntegratedModel`.

        Args:
            variable_names: The parameters to keep among the model inputs.
            use_default_values_as_center: Whether to use the model default values as
                central value of the distributions. If left to ``False``,
                the half sum of the :attr:`~.IntegratedModel.lower_bounds` and
                :attr:`~.IntegratedModel.upper_bounds` of the model is used as
                the central value. Note that only the variables defining both a
                minimum and a maximum bound.
            center_value_expr: A dictionary where keys are the parameter names
                and values the central value of the distribution.
            truncate_to_model_bounds: Whether to truncate the distribution to the
                model bounds.
        """

        self._is_distribution_available(distribution_name)

        if use_default_values_as_center:
            input_names = set(model.default_input_data.keys())
            msg = "no default value"
        else:
            input_names = set(
                set(model.lower_bounds.keys()) & set(model.upper_bounds.keys())
            )
            msg = "no lower and upper bounds"
        if not set(variable_names).issubset(input_names):
            msg = f"Some variables among {variable_names} are not model inputs, or have {msg}."
            raise ValueError(msg)
        input_names = set(input_names & set(variable_names))

        self._check_input_dimension(model, input_names)

        # Reorder input_names according to model.default_input_data to ensure deterministic
        # order:
        reordered_input_names = [
            name for name in model.default_input_data if name in input_names
        ]

        for name in reordered_input_names:
            lb = model.lower_bounds.get(name, None)
            ub = model.upper_bounds.get(name, None)

            if use_default_values_as_center:
                center = model.default_input_data[name]
            else:
                center_value_expr = (
                    self.DEFAULT_CENTER_EXPRESSION
                    if center_value_expr == ""
                    else center_value_expr
                )
                center = self._eval_center_expr(center_value_expr, lb, ub)

            full_options = self._compute_full_options(
                center,
                cov,
                distribution_name,
                center * (1 - sign(center) * cov),
                center * (1 + sign(center) * cov),
                lb if truncate_to_model_bounds else None,
                ub if truncate_to_model_bounds else None,
            )

            size = len(model.default_input_data[name])
            self._filter_options_and_add_variable(
                parameter_space, name, distribution_name, size=size, **full_options
            )
