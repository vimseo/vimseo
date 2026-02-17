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

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from gemseo.utils.metrics.dataset_metric import DatasetMetric
from gemseo.utils.metrics.metric_factory import MetricFactory
from numpy import atleast_1d
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
from vimseo.tools.post_tools.error_scatter_matrix_plot import ErrorScatterMatrix
from vimseo.tools.post_tools.metric_bar_plot import IntegratedMetricBars
from vimseo.tools.post_tools.parallel_coordinates_plot import ParallelCoordinates
from vimseo.tools.post_tools.predict_vs_true_plot import PredictVsTrue
from vimseo.tools.validation_case.validation_case_result import ValidationCaseResult
from vimseo.tools.verification.base_verification import BaseCodeVerificationSettings
from vimseo.utilities.datasets import dataset_to_dataframe
from vimseo.utilities.datasets import encode_vector

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from plotly.graph_objs import Figure


class DeterministicValidationCaseSettings(BaseCodeVerificationSettings):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    output_names: list[str] = Field(
        default=[],
        description="The names of the output on which validation is performed. "
        "By default, consider all the outputs of the reference samples.",
    )


class DeterministicValidationCaseInputs(BaseInputs):
    model: IntegratedModel | None = None
    reference_data: IODataset | None = None
    """The dataset containing the validation test samples."""


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
        reference_data = options["reference_data"]

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

        all_output_data = []
        for i in range(len(reference_data)):
            input_data = {
                k: v[i][~isnan(v[i])]
                for k, v in all_input_data.items()
                if k in input_names
            }

            vector_names = [name for name, data in input_data.items() if len(data) > 1]
            suffix = "".join([
                f"{name}_{encode_vector(input_data[name])}__" for name in vector_names
            ])
            suffix = suffix[:-2]
            new_cache_path = (
                f"{str(self.__orig_cache_path).split(self.__orig_cache_path.suffix)[0]}_"
                f"{suffix}{self.__orig_cache_path.suffix}"
            )
            model.reset_cache(new_cache_path)

            all_output_data.append({
                k: v for k, v in model.execute(input_data).items() if k in output_names
            })

        data = [
            hstack([atleast_1d(v) for v in output_data.values()])
            for output_data in all_output_data
        ]

        # only works for numerical outputs. If a string is considered, data is entirely
        # converted to string
        # TODO check that the outputs are numerical
        doe_dataset = IODataset.from_array(
            data=vstack(data),
            variable_names=list(all_output_data[0].keys()),
            variable_names_to_group_names=dict.fromkeys(
                list(all_output_data[0].keys()), IODataset.OUTPUT_GROUP
            ),
            variable_names_to_n_components={
                k: len(atleast_1d(v)) for k, v in all_output_data[0].items()
            },
        )

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

    def plot_results(
        self,
        result: ValidationCaseResult,
        metric_name: str,
        output_name: str,
        input_names: Sequence[str] = (),
        directory_path: str | Path = "",
        save=False,
        show=True,
        threshold=None,
    ) -> Mapping[str, Figure]:
        """Plot a line plot of simulated versus reference results, and a bar plot of
        metrics values.

        Args:
            metric_name: The name of the error metric to visualize.
            output_name: The name of the output variable to visualize.
            threshold: The threshold used a mid-point for the parallel coordinates plot
                color bar.
        """
        working_directory = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )

        figs = {}

        variable_names = [] if not input_names else [*input_names, output_name]
        df = result.element_wise_metrics.get_view(
            group_names=[IODataset.INPUT_GROUP, metric_name],
            variable_names=variable_names,
        ).copy()
        df.columns = df.get_columns(as_tuple=False)

        figs["parallel_coordinates"] = (
            ParallelCoordinates(working_directory=working_directory)
            .execute(
                df,
                metric_name,
                output_name,
                save=save,
                show=show,
                threshold=threshold,
            )
            .figure
        )

        # Weird inteface: the following plots expect variable names with group suffixes.
        # TODO: document the expected name convention of the dataframe columns.
        df = dataset_to_dataframe(
            result.element_wise_metrics,
            variable_names=variable_names,
            suffix_by_group=True,
        )

        figs["error_scatter_matrix"] = (
            ErrorScatterMatrix(working_directory=working_directory)
            .execute(
                df,
                metric_name,
                output_name,
                save=save,
                show=show,
            )
            .figure
        )

        figs["predict_vs_true"] = (
            PredictVsTrue(working_directory=working_directory)
            .execute(
                df,
                metric_name,
                output_name,
                save=save,
                show=show,
            )
            .figure
        )

        figs["integrated_metric_bars"] = (
            IntegratedMetricBars(working_directory=working_directory)
            .execute(
                result.integrated_metrics,
                metric_name,
                save=save,
                show=show,
            )
            .figure
        )

        return figs
