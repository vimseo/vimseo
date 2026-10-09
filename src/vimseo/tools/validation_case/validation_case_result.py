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

import logging
from collections import defaultdict
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.datasets.io_dataset import IODataset
from numpy import mean
from numpy import ndarray
from pandas import DataFrame
from pydantic import Field

from vimseo.tools.base_tool import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import create_figure
from vimseo.tools.result_visualization import flatten_numbers
from vimseo.tools.validation.validation_point_result import ValidationPointResult
from vimseo.utilities.datasets import GROUP_SEPARATORS
from vimseo.utilities.datasets import dataframe_to_dataset
from vimseo.utilities.datasets import dataset_to_dataframe

if TYPE_CHECKING:
    from collections.abc import Iterable

    from gemseo.datasets.dataset import Dataset

    from vimseo.tools.result_visualization import Figure


LOGGER = logging.getLogger(__name__)


class ValidationCaseVisualizationSettings(BaseVisualizationSettings):
    metric_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the error metrics to visualize. "
        "If empty, use all the metrics of the validation case.",
    )
    output_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the outputs to visualize. "
        "If empty, use all the outputs of the validation case.",
    )
    input_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the inputs shown in the plots. "
        "If empty, use all the inputs.",
    )
    threshold: float | None = Field(
        default=None,
        description="The threshold used as mid-point for the color bar of the "
        "parallel coordinates plot.",
    )


@dataclass
class ValidationCaseResult(BaseResult):
    """The result of a validation case."""

    _VISUALIZATION_SETTINGS: ClassVar[type[ValidationCaseVisualizationSettings]] = (
        ValidationCaseVisualizationSettings
    )

    element_wise_metrics: IODataset | None = None

    integrated_metrics: Mapping[str, Mapping[str, float]] | None = None
    """A dictionary mapping variable names and metric names to integrated metric values
    corresponding the each validation point (i.e. each sample of the reference data)."""

    stochastic_point_results: Sequence[ValidationPointResult] = ()

    def get_common_values(self, data_list: Sequence[list]) -> list:
        """Get the common values across all lists in data_list."""
        common_values = set(data_list[0])
        for data in data_list[1:]:
            common_values.intersection_update(data)
        return sorted(common_values)

    def add_averaged_point(
        self,
        src_group_name: str,
        dataset: Dataset,
        data: dict[str, list],
        output_group_name: str,
    ):
        """Average validation point data and add to case dictionary."""
        group_data = dataset.get_view(group_names=[src_group_name]).copy()
        group_data.columns = group_data.get_columns(as_tuple=False)
        group_data = group_data.mean().to_dict()
        for name, value in group_data.items():
            data[
                f"{name}{GROUP_SEPARATORS[0]}{output_group_name}{GROUP_SEPARATORS[1]}"
            ].append(value)

    def set_from_point_results(self, results: Iterable[ValidationPointResult]):

        # TODO check that all points have common settings
        self.stochastic_point_results = results
        self.metadata = results[0].metadata

        metric_names = self.get_common_values([
            result.metadata.settings["metric_names"] for result in results
        ])
        output_names = self.get_common_values([
            result.metadata.report["measured_output_names"] for result in results
        ])

        data = defaultdict(list)
        for result in results:
            for name, value in result.nominal_data.items():
                # data is then converted to dataframe.
                # arrays are stringified because they could be of different lengths
                if isinstance(value, ndarray) and value.size > 1:
                    value = str(value)
                data[f"{name}{GROUP_SEPARATORS[0]}Nominal{GROUP_SEPARATORS[1]}"].append(
                    value
                )
            for metric_name in metric_names:
                for name, value in result.integrated_metrics[metric_name].items():
                    data[
                        f"{name}{GROUP_SEPARATORS[0]}{metric_name}{GROUP_SEPARATORS[1]}"
                    ].append(value)
            self.add_averaged_point(
                IODataset.INPUT_GROUP,
                result.simulated_data,
                data,
                IODataset.INPUT_GROUP,
            )
            self.add_averaged_point(
                IODataset.OUTPUT_GROUP,
                result.simulated_data,
                data,
                IODataset.OUTPUT_GROUP,
            )
            self.add_averaged_point(
                IODataset.INPUT_GROUP, result.measured_data, data, "ReferenceInputs"
            )
            self.add_averaged_point(
                IODataset.OUTPUT_GROUP, result.measured_data, data, "ReferenceOutputs"
            )

        df = DataFrame.from_dict(data)
        self.element_wise_metrics = dataframe_to_dataset(df)

        # The case integrated metric is the mean of integrated metrics of each validation point.
        self.integrated_metrics = defaultdict(dict)
        for metric_name in metric_names:
            for output_name in output_names:
                self.integrated_metrics[metric_name][output_name] = mean(
                    df[
                        f"{output_name}{GROUP_SEPARATORS[0]}{metric_name}{GROUP_SEPARATORS[1]}"
                    ]
                )

    def _create_figures(
        self, settings: ValidationCaseVisualizationSettings
    ) -> dict[str, Figure]:
        if self.element_wise_metrics is None or not self.integrated_metrics:
            return {}

        from vimseo.tools.post_tools.error_scatter_matrix_plot import ErrorScatterMatrix
        from vimseo.tools.post_tools.metric_bar_plot import IntegratedMetricBars
        from vimseo.tools.post_tools.parallel_coordinates_plot import (
            ParallelCoordinates,
        )
        from vimseo.tools.post_tools.predict_vs_true_plot import PredictVsTrue

        figures = {}
        metric_names = settings.metric_names or tuple(self.integrated_metrics)
        for metric_name in metric_names:
            output_names = settings.output_names or tuple(
                self.integrated_metrics[metric_name]
            )
            for output_name in output_names:
                variable_names = (
                    [*settings.input_names, output_name] if settings.input_names else []
                )
                df = self.element_wise_metrics.get_view(
                    group_names=[IODataset.INPUT_GROUP, metric_name],
                    variable_names=variable_names,
                ).copy()
                df.columns = df.get_columns(as_tuple=False)
                suffix = f"{metric_name}_{output_name}"
                figures[f"parallel_coordinates_{suffix}"] = create_figure(
                    ParallelCoordinates,
                    df,
                    metric_name,
                    output_name,
                    threshold=settings.threshold,
                )

                # These plots expect variable names with group suffixes.
                df = dataset_to_dataframe(
                    self.element_wise_metrics,
                    variable_names=variable_names,
                    suffix_by_group=True,
                )
                figures[f"error_scatter_matrix_{suffix}"] = create_figure(
                    ErrorScatterMatrix, df, metric_name, output_name
                )
                figures[f"predict_vs_true_{suffix}"] = create_figure(
                    PredictVsTrue, df, metric_name, output_name
                )

            figures[f"integrated_metric_bars_{metric_name}"] = create_figure(
                IntegratedMetricBars, self.integrated_metrics, metric_name
            )
        return figures

    def get_key_values(self) -> dict[str, float]:
        key_values = flatten_numbers(self.integrated_metrics or {})
        if self.element_wise_metrics is None or not self.integrated_metrics:
            return key_values

        # The metrics of each validation point, e.g. "AreaMetric.y.point_0".
        for metric_name, output_names in self.integrated_metrics.items():
            if metric_name not in self.element_wise_metrics.group_names:
                continue
            variable_names = self.element_wise_metrics.get_variable_names(metric_name)
            for output_name in output_names:
                if output_name not in variable_names:
                    continue
                values = self.element_wise_metrics.get_view(
                    group_names=metric_name, variable_names=output_name
                ).to_numpy()
                key_values.update(
                    flatten_numbers({
                        f"{metric_name}.{output_name}.point_{i}": value
                        for i, value in enumerate(values[:, 0])
                    })
                )
        return key_values
