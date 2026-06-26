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
#        :author: Jorge CAMACHO-CASERO, Ludovic BARRIERE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gemseo.algos.design_space import DesignSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.scenarios.doe_scenario import DOEScenario
from gemseo.utils.directory_creator import DirectoryNamingMethod
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.doe.doe import _set_output_names
from vimseo.tools.doe.doe_result import DOEResult

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class CustomDOESettings(BaseSettings):
    input_names: list[str] = Field(
        default=[],
        description="The names of the variables defining the input variables on which "
        "the DOE is executed. If left to default value, all variable in group "
        "``IODataset.INPUT_GROUP`` of ``input_dataset`` are considered.",
    )
    output_names: list[str] = Field(
        default=[],
        description="The names of the variables computed by the model. If left to "
        "default value, all output variables of the model are considered.",
    )


class CustomDOEInputs(BaseInputs):
    model: IntegratedModel | None = None
    input_dataset: Dataset | None = Field(
        default=None,
        description="A dataset containing at least a group named "
        "``IODataset.INPUT_GROUP``. "
        "The model is run on the samples defined by this group.",
    )


class CustomDOETool(BaseAnalysisTool):
    """Run a Custom DOE executing an :class:`~.IntegratedModel` over a
    :class:`~.gemseo.algos.parameter_space.ParameterSpace`."""

    results: DOEResult
    """The results of a :class:`~.CustomDOETool`."""

    _INPUTS = CustomDOEInputs

    _SETTINGS = CustomDOESettings

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
        self.result = DOEResult()

    @BaseTool.validate
    def execute(
        self,
        inputs: CustomDOEInputs | None = None,
        settings: CustomDOESettings | None = None,
        **options,
    ) -> DOEResult:
        model = options["model"]
        input_dataset = options["input_dataset"]
        load_case = model.load_case.name
        doe_name = f"DOE_{model.name}_{load_case}_CustomDOE"

        input_names = (
            input_dataset.get_variable_names(group_name=IODataset.INPUT_GROUP)
            if len(options["input_names"]) == 0
            else options["input_names"]
        )
        if not set(input_names).issubset(set(model.get_input_data_names())):
            LOGGER.warning(
                "Some of the specified input names are not "
                f"input variables of the model: {set(input_names) - set(model.get_input_data_names())}. "
            )
            input_names = [
                name for name in input_names if name in model.get_input_data_names()
            ]

        output_names = _set_output_names(model, options["output_names"])

        design_space = DesignSpace()
        for name in input_names:
            design_space.add_variable(
                name, size=input_dataset.variable_names_to_n_components[name]
            )

        scenario = DOEScenario(
            [model],
            output_names[0],
            design_space,
            formulation_name="DisciplinaryOpt",
        )
        if len(output_names) > 1:
            for name in output_names[1:]:
                scenario.add_observable(name)

        samples = input_dataset.get_view(variable_names=input_names).to_numpy()
        scenario.execute(algo_name="CustomDOE", samples=samples)
        self.result.dataset = scenario.to_dataset(name=doe_name, opt_naming=False)
        return self.result
