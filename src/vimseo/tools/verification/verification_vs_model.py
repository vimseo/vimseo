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

"""A tool to verify a model against another model.

The parameter space explored during the verificationc can be a dataset or a
``ParameterSpace``, e.g. built from a ``SpaceTool``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.verification.base_verification import BaseCodeVerificationSettings
from vimseo.tools.verification.base_verification import BaseVerification

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.tools.verification.verification_result import VerificationResult


class CodeVerificationAgainstModelInputs(BaseInputs):
    model: IntegratedModel | None = None
    reference_model: IntegratedModel | None = None
    input_dataset: Dataset | None = None


# TODO add observed output names.
class CodeVerificationAgainstModel(BaseVerification):
    """Perform a code verification on a model based on another model and a Dataset
    providing the samples where the model is executed."""

    _INPUTS = CodeVerificationAgainstModelInputs

    _SETTINGS = BaseCodeVerificationSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        reference_doe = CustomDOETool(name="ReferenceCustomDOETool")
        super().__init__(
            subtools=[CustomDOETool(), reference_doe],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: CodeVerificationAgainstModelInputs | None = None,
        settings: BaseCodeVerificationSettings | None = None,
        **options,
    ) -> VerificationResult:
        model = options["model"]
        reference_model = options["reference_model"]
        input_dataset = options["input_dataset"]

        self.result._fill_metadata(options["description"], model.description)
        self.result.metadata.misc["reference_model"] = reference_model.description

        self._output_names = (
            reference_model.get_output_data_names(remove_metadata=True)
            if len(options["output_names"]) == 0
            else options["output_names"]
        )

        if Dataset.DEFAULT_GROUP in input_dataset.group_names:
            input_dataset.rename_group(Dataset.DEFAULT_GROUP, IODataset.INPUT_GROUP)

        doe_dataset = (
            self
            ._subtools["CustomDOETool"]
            .execute(
                model=model,
                input_dataset=input_dataset,
                # TODO a method get_extended_output_names(),
                #  to be used in DOE on model in all comparison tools
                output_names=self.get_extended_output_names(),
            )
            .dataset
        )
        reference_doe_dataset = (
            self
            ._subtools["ReferenceCustomDOETool"]
            .execute(
                model=reference_model,
                input_dataset=input_dataset,
                output_names=self._output_names,
            )
            .dataset
        )
        element_wise_metrics, integrated_metrics = self._compute_comparison(
            reference_doe_dataset, doe_dataset
        )
        simulation_and_reference, element_wise_metrics = self._post(
            doe_dataset, reference_doe_dataset, element_wise_metrics
        )
        self.result.simulation_and_reference = simulation_and_reference
        self.result.element_wise_metrics = element_wise_metrics
        self.result.integrated_metrics = integrated_metrics

        return self.result
