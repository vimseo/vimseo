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

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from gemseo.utils.metrics.dataset_metric import DatasetMetric
from gemseo.utils.metrics.metric_factory import MetricFactory
from numpy import hstack
from numpy import isnan
from numpy import vstack
from pydantic import ConfigDict
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.model_metadata import MetaDataNames
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.validation_case.validation_case_result import ValidationCaseResult
from vimseo.tools.verification.base_verification import BaseCodeVerificationSettings
from vimseo.utilities.datasets import DatasetInput
from vimseo.utilities.datasets import encode_vector
from vimseo.utilities.datasets import resolve_io_groups

if TYPE_CHECKING:
    from collections.abc import Sequence


class DeterministicValidationCaseSettings(BaseCodeVerificationSettings):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    output_names: list[str] = Field(
        default=[],
        description="The names of the output on which validation is performed. "
        "By default, consider all the outputs of the reference samples.",
    )


class DeterministicValidationCaseInputs(BaseInputs):
    model: IntegratedModel | None = None
    reference_data: DatasetInput | None = None
    """The validation test samples, either as a mapping of variable names to values, a
    DataFrame or a dataset."""


class DeterministicValidationCase(BaseAnalysisTool):
    """Suppose we want to validate a model ove a given validation domain.

    We define validation point as one of the points chosen to map this domain.
    """

    name: str
    """The name of the validation point."""

    results: ValidationCaseResult

    _INPUTS = DeterministicValidationCaseInputs

    _SETTINGS = DeterministicValidationCaseSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        """
        Args:
            reference_data: The reference data against which the simulated data are
            compared.
            metric_names: the names of the :class:`.BaseMetric` used to compute
            the validation errors.
        """
        super().__init__(
            subtools=[CustomDOETool()],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )

        self.result = ValidationCaseResult()

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: DeterministicValidationCaseInputs | None = None,
        settings: DeterministicValidationCaseSettings | None = None,
        **options,
    ) -> ValidationCaseResult:

        model = options["model"]
        reference_data = resolve_io_groups(
            options["reference_data"],
            model=model,
            input_names=options["input_names"],
            output_names=options["output_names"],
        )

        self.result.metadata.model = model.description
        self.result.metadata.report["title"] = (
            f"Validation of {model.name} {model.load_case.name}"
        )

        input_names = (
            reference_data.get_variable_names(group_name=IODataset.INPUT_GROUP)
            if len(options["input_names"]) == 0
            else options["input_names"]
        )

        all_input_data = reference_data.to_dict_of_arrays(by_group=True)[
            IODataset.INPUT_GROUP
        ]

        output_names = (
            [
                name
                for name in model.get_output_data_names()
                if name not in [k.name for k in MetaDataNames]
            ]
            if not options["output_names"]
            else options["output_names"]
        )

        self.__orig_cache_path = Path(model._cache_file_path)

        # The NaN padding the vectors of the reference data is removed, so that the
        # size of a vector input can change from a sample to another. The samples
        # sharing the same vector inputs share a cache file, and are simulated together
        # by the DOE tool, which needs inputs of the same size for all its samples.
        sample_indices_per_cache = defaultdict(list)
        input_data_per_sample = []
        for i in range(len(reference_data)):
            input_data = {
                k: v[i][~isnan(v[i])]
                for k, v in all_input_data.items()
                if k in input_names
            }
            input_data_per_sample.append(input_data)

            vector_names = [name for name, data in input_data.items() if len(data) > 1]
            suffix = "".join([
                f"{name}_{encode_vector(input_data[name])}__" for name in vector_names
            ])
            suffix = suffix[:-2]
            cache_path = (
                f"{str(self.__orig_cache_path).split(self.__orig_cache_path.suffix)[0]}_"
                f"{suffix}{self.__orig_cache_path.suffix}"
            )
            sample_indices_per_cache[cache_path].append(i)

        doe_tool = self._subtools["CustomDOETool"]
        output_data_per_sample = [None] * len(reference_data)
        simulation_run_ids = {}
        for cache_path, sample_indices in sample_indices_per_cache.items():
            model.reset_cache(cache_path)
            first_input_data = input_data_per_sample[sample_indices[0]]
            input_dataset = IODataset.from_array(
                data=vstack([
                    hstack(list(input_data_per_sample[i].values()))
                    for i in sample_indices
                ]),
                variable_names=list(first_input_data),
                variable_names_to_n_components={
                    name: len(data) for name, data in first_input_data.items()
                },
                variable_names_to_group_names=dict.fromkeys(
                    first_input_data, IODataset.INPUT_GROUP
                ),
            )
            group_dataset = doe_tool.execute(
                model=model, input_dataset=input_dataset, output_names=output_names
            ).dataset
            simulation_run_ids.update(
                dict.fromkeys(doe_tool.result.metadata.simulation_run_ids)
            )
            output_data = group_dataset.get_view(
                group_names=IODataset.OUTPUT_GROUP, variable_names=output_names
            ).to_numpy()
            for i, sample_output_data in zip(sample_indices, output_data, strict=True):
                output_data_per_sample[i] = sample_output_data

        # only works for numerical outputs. If a string is considered, data is entirely
        # converted to string
        # TODO check that the outputs are numerical
        doe_dataset = IODataset.from_array(
            data=vstack(output_data_per_sample),
            variable_names=output_names,
            variable_names_to_group_names=dict.fromkeys(
                output_names, IODataset.OUTPUT_GROUP
            ),
            variable_names_to_n_components={
                name: group_dataset.variable_names_to_n_components[name]
                for name in output_names
            },
        )

        if len(sample_indices_per_cache) > 1:
            # The DOE tool holds the result of its last execution only: it is
            # given all the samples, so that its exported result is complete. Each
            # execution is archived with its own samples.
            doe_tool.result.dataset = self.__gather_samples(
                reference_data, input_names, doe_dataset
            )
            doe_tool.result.metadata.simulation_run_ids = tuple(simulation_run_ids)

        error_dataset = Dataset()
        error_dataset.add_group(
            group_name=IODataset.INPUT_GROUP,
            data=reference_data.get_view(
                variable_names=input_names, group_names=IODataset.INPUT_GROUP
            ).to_numpy(),
            variable_names=input_names,
            variable_names_to_n_components=reference_data.variable_names_to_n_components,
        )
        # Each metric is applied to all output_names
        self.result.integrated_metrics = defaultdict(dict)
        for metric_name in options["metric_names"]:
            metric = MetricFactory().create(metric_name)
            dm = DatasetMetric(
                metric,
                variable_names=output_names,
            )
            error_ds = dm.compute(doe_dataset, reference_data)
            error_dataset.add_group(
                group_name=metric_name,
                variable_names=output_names,
                data=error_ds.get_view().to_numpy(),
                variable_names_to_n_components=error_ds.group_names_to_n_components,
            )
            for output_name in output_names:
                dm = DatasetMetric(
                    metric,
                    variable_names=output_name,
                )
                mean_metric = MetricFactory().create("MeanMetric", dm)
                self.result.integrated_metrics[metric_name][output_name] = (
                    mean_metric.compute(
                        doe_dataset,
                        reference_data,
                    )
                )

        error_dataset.add_group(
            group_name=IODataset.OUTPUT_GROUP,
            data=doe_dataset.get_view(
                variable_names=output_names,
                group_names=IODataset.OUTPUT_GROUP,
            ).to_numpy(),
            variable_names=output_names,
            variable_names_to_n_components=doe_dataset.variable_names_to_n_components,
        )

        error_dataset.add_group(
            group_name="ReferenceOutputs",
            data=reference_data.get_view(
                variable_names=output_names,
                group_names=IODataset.OUTPUT_GROUP,
            ).to_numpy(),
            variable_names=output_names,
            variable_names_to_n_components=reference_data.variable_names_to_n_components,
        )

        self.result.element_wise_metrics = error_dataset

        return self.result

    @staticmethod
    def __gather_samples(
        reference_data: IODataset, input_names: Sequence[str], doe_dataset: IODataset
    ) -> IODataset:
        """Return the inputs and the outputs of all the samples.

        Args:
            reference_data: The reference data, whose vector inputs are padded with NaN.
            input_names: The names of the inputs.
            doe_dataset: The outputs of the samples, in the order of the reference data.

        Returns:
            The inputs of the reference data, padded with NaN, and the outputs.
        """
        dataset = IODataset()
        dataset.add_group(
            group_name=IODataset.INPUT_GROUP,
            data=reference_data.get_view(
                variable_names=input_names, group_names=IODataset.INPUT_GROUP
            ).to_numpy(),
            variable_names=input_names,
            variable_names_to_n_components={
                name: reference_data.variable_names_to_n_components[name]
                for name in input_names
            },
        )
        dataset.add_group(
            group_name=IODataset.OUTPUT_GROUP,
            data=doe_dataset.get_view(group_names=IODataset.OUTPUT_GROUP).to_numpy(),
            variable_names=doe_dataset.get_variable_names(IODataset.OUTPUT_GROUP),
            variable_names_to_n_components=doe_dataset.variable_names_to_n_components,
        )
        return dataset
