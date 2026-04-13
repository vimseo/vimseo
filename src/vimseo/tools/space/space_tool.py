# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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
#        :author: Jorge CAMACHO-CASERO, Ludovic BARRIERE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from gemseo.uncertainty.distributions.base_distribution import (
    InterfacedDistributionSettings,
)
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import inf
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.lib.space_builder_factory import SpaceBuilderFactory
from vimseo.tools.space.space_tool_result import SpaceToolResult
from vimseo.tools.statistics.statistics_tool import StatisticsResult

if TYPE_CHECKING:
    from collections.abc import Mapping

    from plotly.graph_objs import Figure


def update_space_from_statistics(
    parameter_space: ParameterSpace,
    statistics_results: StatisticsResult,
    model: IntegratedModel | None = None,
):
    """Add random variables to a parameter space from a :class:`.StatisticsResult`."""
    variable_names = statistics_results.analysis.names
    for name in variable_names:
        if name in parameter_space.variable_names:
            parameter_space.remove_variable(name)

        distribution = statistics_results.analysis.distributions[name]
        parameter_space.add_random_variable(
            name,
            "OTDistribution",
            settings=InterfacedDistributionSettings(
                name=distribution.name,
                parameters=distribution.value.settings["parameters"],
                lower_bound=(
                    max(
                        (model.lower_bounds.get(name, -inf)),
                        distribution.value.math_lower_bound,
                    )
                    if model is not None
                    else None
                ),
                upper_bound=(
                    min(
                        (model.upper_bounds.get(name, inf)),
                        distribution.value.math_upper_bound,
                    )
                    if model is not None
                    else None
                ),
            ),
        )


class SpaceToolSettings(BaseSettings):
    distribution_name: str = "OTTriangularDistribution"
    space_builder_name: str = "FromModelCenterAndCov"
    minimum_values: dict[str, float] | None = Field(
        default=None, description="The mapping between names and minimum values."
    )
    maximum_values: dict[str, float] | None = Field(
        default=None, description="The mapping between names and maximum values."
    )
    center_value_expr: str = ""
    use_default_values_as_center: bool = True
    variable_names: list[str] = Field(default=[], description="List of variable names")
    center_values: dict[str, float] | None = Field(
        default=None, description="The mapping between names and central values."
    )
    cov: Annotated[float, Field(strict=True, gt=0)] = (
        0.05  # confloat(strict=True, gt=0) = 0.05
    )
    truncate_to_model_bounds: bool = True
    lower_bounds: dict[str, float | None] | None = Field(
        default=None, description="The mapping between names and lower bounds."
    )
    upper_bounds: dict[str, float | None] | None = Field(
        default=None, description="The mapping between names and upper bounds."
    )
    size: int = 1


class StreamlitSpaceToolSettings(SpaceToolSettings):
    """The ``SpaceToolSettings`` for the workflow Streamlit dashboard."""

    minimum_values: dict[str, float] = Field(
        default={}, description="The mapping between names and minimum values."
    )
    maximum_values: dict[str, float] = Field(
        default={}, description="The mapping between names and maximum values."
    )
    center_values: dict[str, float] = Field(
        default={}, description="The mapping between names and central values."
    )
    lower_bounds: dict[str, float] = Field(
        default={}, description="The mapping between names and lower bounds."
    )
    upper_bounds: dict[str, float] = Field(
        default={}, description="The mapping between names and upper bounds."
    )

    def model_post_init(self, __context: Any) -> None:
        dict_attr_names = [
            "minimum_values",
            "maximum_values",
            "center_values",
            "lower_bounds",
            "upper_bounds",
        ]
        for attr_name in dict_attr_names:
            attr = getattr(self, attr_name)
            attr = None if attr == {} else attr
            setattr(self, attr_name, attr)


class SpaceToolInputs(BaseInputs):
    statistics: StatisticsResult | None = None
    model: IntegratedModel | None = None


# TODO Add check of generated param space versus model input grammar?
class SpaceTool(BaseAnalysisTool):
    """A tool to build a space of parameters.

    This class updates a :class:`~.gemseo.algos.parameter_space.ParameterSpace`
    based on a :class:`~.SpaceBuilder`.
    Four space builders are available.
    Two of them are based on user-data and construct the parameter space based on
    either (min, max) values or (center, coefficient of variation around the center)
    values.
    The two other are based on an :class:`~.IntegratedModel`. Similarly, the parameter
    space is based either on the (min, max) values of the model inputs, or on
    (center, coefficient of variation around the center) values. In the latter case,
    an option allows to define the center values either as the half sum of the model
    input min and max (this default behaviour can be modifed by passing a symbolic
    expression), or on the model default input values.
    values.

    Examples:
        >>> from vimseo.tools.space.space_tool import SpaceTool
        >>> # Start from an empty parameter space.
        >>> space_tool = SpaceTool()
        >>> # Update it based on user-defined center values
        >>> # and a coefficient of variation using the "FromCenterAndCov" builder.
        >>> space_tool.update(
        ...     "OTNormalDistribution",
        ...     "FromCenterAndCov",
        ...     center_values={"force_relative_location": 0.5},
        ...     cov=0.05,
        ... )
        >>> # Then, a new update can be done using a "FromMinAndMax" builder,
        >>> # to which minimum and maximum values are passed.
        >>> space_tool.update(
        ...     "OTTriangularDistribution",
        ...     "FromMinAndMax",
        ...     minimum_values={"young_modulus": 1e5},
        ...     maximum_values={"young_modulus": 1.5e5},
        ... )
        >>> # By default the center of the distribution is the half sum of the min
        >>> # and max values.
        >>> # But this behaviour can be changed by passing a symbolic expression,
        >>> # having the parameters "minimum" and "maximum":
        >>> space_tool.update(
        ...     "OTTriangularDistribution",
        ...     "FromMinAndMax",
        ...     minimum_values={"young_modulus": 1e5},
        ...     maximum_values={"young_modulus": 1.5e5},
        ...     center_value_expr="{0.25 * {minimum} + 0.75 * {maximum}",
        ... )
        >>> # It is convenient to define the initial parameter space from a model.
        >>> # Here the "FromModelMinAndMax" builder is used.
        >>> # A model must first be instanciated.
        >>> from vimseo.api import create_model
        >>> model = create_model("BendingTestAnalytical", "Cantilever")
        >>> space_tool.update(
        ...     distribution_name,
        ...     "FromModelMinAndMax",
        ...     model=model,
        ...     variable_names=["E", "force_relative_location"],
        ...     use_default_values_as_center=True,
        ... )
        >>> # The ``variable_names`` argument allows to retain only a subset of
        >>> # variables, while the ``use_default_values_as_center`` allows to define the
        >>> # center of the distributions as the model default input values.
        >>> # If ``use_default_values_as_center`` is set to ``False``, the half sum
        >>> # between the model min and max values is used by default.
        >>> # Similarly to the "FromMinAndMax" builder, a symbolic expression can be
        >>> # used to customize the center value based on the min and max values of the
        >>> # model inputs:
        >>> space_tool.update(
        ...     distribution_name,
        ...     "FromModelMinAndMax",
        ...     model=model,
        ...     variable_names=["E", "force_relative_location"],
        ...     use_default_values_as_center=False,
        ...     center_value_expr="{0.25 * {minimum} + 0.75 * {maximum}",
        ... )
        >>> # A parameter space can also be updated from a model using center values
        >>> # and a coefficient of variation:
        >>> space_tool.update(
        ...     distribution_name,
        ...     "FromModelCenterAndCov",
        ...     model=model,
        ...     variable_names=["E", "force_relative_location"],
        ...     use_default_values_as_center=False,
        ...     cov=0.05,
        ... )
        >>> # where the definition of the distribution center is the same as for the
        >>> # "FromModelMinAndMax" builder.
    """

    results: SpaceToolResult
    """The results of this tool."""

    _INPUTS = SpaceToolInputs

    _SETTINGS = SpaceToolSettings

    _STREAMLIT_SETTINGS = StreamlitSpaceToolSettings

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
        self.result = SpaceToolResult()
        if not self.result.parameter_space:
            self.result.parameter_space = ParameterSpace()
        self.__builder_factory = SpaceBuilderFactory()
        self._space_builder = None

    def update(
        self,
        distribution_name: str = "",
        space_builder_name: str = "",
        model=None,
        **options,
    ) -> None:
        """Updates the space of parameters.

        Args:
            distribution_name: The name of the distribution.
            space_builder_name: The name of the :class:`~.SpaceBuilder`.
            model: The model from which the space of parameters is built.
            options: The options of the parameter space builder.
        """
        if options["statistics"] is not None:
            self.result.parameter_space = ParameterSpace()
            update_space_from_statistics(
                self.result.parameter_space, options["statistics"]
            )
        else:
            self._space_builder = self.__builder_factory.create(space_builder_name)
            self._space_builder.update_options(**options)
            options = self._space_builder.get_filtered_options(
                **self._space_builder.options
            )
            self._space_builder._check_options(**options)
            self._space_builder.build(
                self.result.parameter_space, distribution_name, model=model, **options
            )

    @BaseTool.validate
    def execute(
        self,
        inputs: SpaceToolInputs | None = None,
        setting: SpaceToolSettings | None = None,
        **options,
    ) -> SpaceToolResult:
        self.update(**options)
        return self.result

    def plot_results(
        self,
        result: SpaceToolResult,
        save=False,
        show=True,
        directory_path: str | Path = "",
        n_samples=10,
        **options,
    ) -> Mapping[str, Figure]:
        """

        Args:
            n_samples: The number of samples used to represent the parameter space.

        Returns:

        """
        dataset = Dataset.from_array(
            data=result.parameter_space.compute_samples(n_samples),
            variable_names=result.parameter_space.uncertain_variables,
        )
        plot = ScatterMatrix(dataset)
        return plot.execute(
            save=save,
            show=show,
            directory_path=(
                self.working_directory if directory_path == "" else Path(directory_path)
            ),
            **options,
        )

    @property
    def parameter_space(self):
        return self.result.parameter_space

    @classmethod
    def get_available_space_builders(cls):
        """The available :class:`.SpaceBuilder`."""
        return SpaceBuilderFactory().class_names
        # space_builders.remove("SpaceBuilder")

    def get_available_distributions(self):
        """The available distributions for the current space builder."""
        return self._space_builder.get_available_distributions()
