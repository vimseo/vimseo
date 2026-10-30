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

from typing import TYPE_CHECKING

from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.analysis_nodes.base_composite_analysis_node import BaseCompositeAnalysisNode
from vimseo.analysis_nodes.design_value.design_value_result import DesignValueResult
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.analysis_nodes.doe.doe import DOEInputs
from vimseo.analysis_nodes.doe.doe import DOESettings
from vimseo.analysis_nodes.statistics.statistics_analysis_node import (
    StatisticsAnalysisNode,
)
from vimseo.analysis_nodes.statistics.statistics_analysis_node import StatisticsSettings
from vimseo.config.global_configuration import _configuration as config

if TYPE_CHECKING:
    from pathlib import Path


class DesignValueInputs(DOEInputs):
    """Inputs of a design value analysis node."""


# TODO remove field 'variable_names'. Try a mechanism to remove fields
class DesignValueSettings(StatisticsSettings, DOESettings):
    """The Design value analysis node settings."""

    # stochastic_input_names: list[str] = Field(
    #     default=[],
    #     description="The names of the input variables to be added to the input "
    #     "``parameter_space``. The appended parameter space is used as input of the DOE. "
    #     "Since only material properties may be stochastic, "
    #     "these names should be material properties, "
    #     "for which a probability distribution is defined.",
    # )
    # TODO remove ``variable_names`` setting


class DesignValueAnalysisNode(BaseCompositeAnalysisNode):
    """Provide methods for calculating Parametric and Empirical statistics for a given
    dataset."""

    result: DesignValueResult

    _INPUTS = DesignValueInputs

    _SETTINGS = DesignValueSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            sub_analysis_nodes=[DOEAnalysisNode(), StatisticsAnalysisNode()],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )
        self.result = DesignValueResult()

    @BaseCompositeAnalysisNode._validate
    def execute(
        self,
        inputs: DesignValueInputs | None = None,
        settings: DesignValueSettings | None = None,
        **options,
    ) -> DesignValueResult:
        # input_parameter_space = options["parameter_space"]
        # stochastic_input_names = options["stochastic_input_names"]
        model = options["model"]
        # if len(stochastic_input_names) > 0:
        #     material_parameter_space = model.material.to_parameter_space()
        #     if not set(stochastic_input_names).issubset(
        #         set(material_parameter_space.uncertain_variables)
        #     ):
        #         raise ValueError(
        #             "Some stochastic names are not contained in the model "
        #             "input stochastic variables which are "
        #             f"{material_parameter_space.uncertain_variables}."
        #         )
        #     for name in stochastic_input_names:
        #         input_parameter_space[name] = material_parameter_space[name]

        doe_analysis_node = self._sub_analysis_nodes["DOEAnalysisNode"]

        if len(options["output_names"]) > 0:
            output_names = options["output_names"]
        else:
            output_names = model.output_grammar.names
            for name in model.get_metadata_names():
                output_names.remove(name)

        doe_options = doe_analysis_node.get_filtered_options(**options)
        del doe_options["output_names"]
        dataset = doe_analysis_node.execute(
            output_names=output_names, **doe_options
        ).dataset

        statistics_analysis_node = self._sub_analysis_nodes["StatisticsAnalysisNode"]
        statistics_options = statistics_analysis_node.get_filtered_options(**options)
        statistics_options["variable_names"] = output_names
        # TODO why is dataset not contained in statistics_options?
        statistics_analysis_node.execute(dataset=dataset, **statistics_options)
        self.result = statistics_analysis_node.result
