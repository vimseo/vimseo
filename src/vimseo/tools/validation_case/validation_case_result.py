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

import logging
from collections import defaultdict
from dataclasses import field
from typing import TYPE_CHECKING

from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.metrics.dataset_metric import DatasetMetric
from gemseo.utils.metrics.metric_factory import MetricFactory
from numpy import ndarray
from pandas import DataFrame

from vimseo.tools.base_tool import BaseResult
from vimseo.utilities.datasets import dataframe_to_dataset

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence

    from gemseo.datasets.dataset import Dataset

    from vimseo.tools.validation.validation_point_result import ValidationPointResult

LOGGER = logging.getLogger(__name__)


class ValidationCaseResult(BaseResult):
    """The result of a validation case."""

    element_wise_metrics: IODataset | None = field(default_factory=None)

    integrated_metrics: Mapping[str, Mapping[str, float]] | None = None
    """A dictionary mapping variable names and metric names to integrated metric values
    corresponding the each validation point (i.e. each sample of the reference data)."""

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
            data[f"{name}[{output_group_name}]"].append(value)

    def set_from_point_results(self, results: Iterable[ValidationPointResult]):

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
                data[f"{name}[Nominal]"].append(value)
            for metric_name in metric_names:
                for name, value in result.integrated_metrics[metric_name].items():
                    data[f"{name}[{metric_name}]"].append(value)
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

        self.integrated_metrics = defaultdict(dict)
        for metric_name in metric_names:
            metric = MetricFactory().create(metric_name)
            for output_name in output_names:
                dm = DatasetMetric(
                    metric,
                    variable_names=output_name,
                )
                mean_metric = MetricFactory().create("MeanMetric", dm)
                self.integrated_metrics[metric_name][output_name] = mean_metric.compute(
                    self.element_wise_metrics.get_view(
                        group_names=[f"{IODataset.OUTPUT_GROUP}"],
                        variable_names=[output_name],
                    ),
                    self.element_wise_metrics.get_view(
                        group_names=["ReferenceOutputs"],
                        variable_names=[output_name],
                    ),
                )
