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

"""A tool to verify a model against a reference dataset."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.verification.base_verification import BaseCodeVerificationSettings
from vimseo.tools.verification.base_verification import BaseVerification
from vimseo.tools.verification.base_verification import check_output_names

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.tools.verification.verification_result import VerificationResult


class CodeVerificationAgainstDataInputs(BaseInputs):
    model: IntegratedModel | None = None
    reference_data: IODataset | None = None


class CodeVerificationAgainstData(BaseVerification):
    """Perform a code verification on a model based on a dataset providing input and
    reference output values."""

    _INPUTS = CodeVerificationAgainstDataInputs

    _SETTINGS = BaseCodeVerificationSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        super().__init__(
            subtools=[CustomDOETool()],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )

    # TODO: pass control_outputs arg. if None, use metric_name applied to all output
    #  variables.
    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: CodeVerificationAgainstDataInputs | None = None,
        settings: BaseCodeVerificationSettings | None = None,
        **options,
    ) -> VerificationResult:
        model = options["model"]
        reference_data = options["reference_data"]

        self.result._fill_metadata(options["description"], model.description)

        input_names = (
            options["reference_data"].get_variable_names(
                group_name=IODataset.INPUT_GROUP
            )
            if len(options["input_names"]) == 0
            else options["input_names"]
        )

        self._output_names = (
            reference_data.get_variable_names(group_name=IODataset.OUTPUT_GROUP)
            if not options["output_names"]
            else options["output_names"]
        )
        check_output_names(self._output_names, model)

        doe_dataset = (
            self
            ._subtools["CustomDOETool"]
            .execute(
                model=model,
                input_dataset=reference_data,
                input_names=input_names,
                output_names=self.get_extended_output_names(),
            )
            .dataset
        )
        element_wise_metrics, integrated_metrics = self._compute_comparison(
            reference_data, doe_dataset
        )
        element_wise_metrics.add_group(
            group_name=IODataset.INPUT_GROUP,
            data=reference_data.get_view(
                variable_names=input_names, group_names=IODataset.INPUT_GROUP
            ).to_numpy(),
            variable_names=input_names,
            variable_names_to_n_components=reference_data.variable_names_to_n_components,
        )
        doe_dataset.add_group(
            group_name="Reference",
            data=reference_data.get_view(
                variable_names=self._output_names,
                group_names=IODataset.OUTPUT_GROUP,
            ).to_numpy(),
            variable_names=self._output_names,
            variable_names_to_n_components=reference_data.variable_names_to_n_components,
        )

        # simulation_and_reference, _ = self._post(
        #     doe_dataset, reference_data, element_wise_metrics.copy()
        # )
        self.result.simulation_and_reference = doe_dataset
        self.result.element_wise_metrics = element_wise_metrics
        self.result.integrated_metrics = integrated_metrics

        return self.result
