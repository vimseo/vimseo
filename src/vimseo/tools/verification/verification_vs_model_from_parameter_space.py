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

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.utils.directory_creator import DirectoryNamingMethod
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.doe.doe import DOESettings
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.verification.base_verification import BaseVerification
from vimseo.tools.verification.base_verification import check_output_names
from vimseo.tools.verification.verification_result import CASE_DESCRIPTION_TYPE

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.tools.verification.verification_result import VerificationResult


class CodeVerificationAgainstModelFromPSSettings(DOESettings):
    metric_names: list[str] = Field(
        default=["SquaredErrorMetric"],
        description="The default metric that applies to all model output variables.",
    )

    description: CASE_DESCRIPTION_TYPE | None = None


class CodeVerificationAgainstModelFromPSInputs(BaseInputs):
    model: IntegratedModel | None = None
    reference_model: IntegratedModel | None = None
    parameter_space: ParameterSpace = ParameterSpace()


class CodeVerificationAgainstModelFromParameterSpace(BaseVerification):
    """Perform a code verification on a model based on another model and a
    ``ParameterSpace``."""

    _INPUTS = CodeVerificationAgainstModelFromPSInputs

    _SETTINGS = CodeVerificationAgainstModelFromPSSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        super().__init__(
            subtools=[DOETool(), DOETool(name="ReferenceDOETool")],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: CodeVerificationAgainstModelFromPSInputs | None = None,
        settings: CodeVerificationAgainstModelFromPSSettings | None = None,
        **options,
    ) -> VerificationResult:
        model = options["model"]
        reference_model = options["reference_model"]

        self._output_names = (
            reference_model.get_output_data_names(remove_metadata=True)
            if not options["output_names"]
            else options["output_names"]
        )
        check_output_names(self._output_names, model)

        self.result._fill_metadata(options["description"], model.description)
        self.result.metadata.misc["reference_model"] = reference_model.description

        doe_dataset = (
            self
            ._subtools["DOETool"]
            .execute(
                model=model,
                parameter_space=options["parameter_space"],
                output_names=self.get_extended_output_names(),
                n_samples=options["n_samples"],
                algo=options["algo"],
                # algo_options=options["algo_options"],
            )
            .dataset
        )
        reference_doe_dataset = (
            self
            ._subtools["ReferenceDOETool"]
            .execute(
                model=reference_model,
                parameter_space=options["parameter_space"],
                output_names=self._output_names,
                n_samples=options["n_samples"],
                algo=options["algo"],
                # algo_options=options["algo_options"],
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
