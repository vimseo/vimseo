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
from operator import ge
from typing import TYPE_CHECKING

from gemseo.datasets.io_dataset import IODataset
from gemseo.problems.mdo.scalable.parametric.core import variable_names
from gemseo.utils.metrics import element_wise_metric
from numpy import ndarray
from pandas import DataFrame

from vimseo.tools.base_tool import BaseResult
from vimseo.utilities.datasets import dataframe_to_dataset
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from gemseo.utils.metrics.dataset_metric import DatasetMetric
from gemseo.utils.metrics.metric_factory import MetricFactory
f
if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from vimseo.tools.validation.validation_point_result import ValidationPointResult

LOGGER = logging.getLogger(__name__)


class ValidationCaseResult(BaseResult):
    """The result of a validation case."""

    element_wise_metrics: IODataset | None = field(default_factory=None)

    integrated_metrics: Mapping[str, Mapping[str, float]] | None = None
    """A dictionary mapping variable names and metric names to integrated metric values
    corresponding the each validation point (i.e. each sample of the reference data)."""

    def set_from_point_results(self, results: Iterable[ValidationPointResult]):

        all_metric_names = [result.metadata.settings["metric_names"] for result in results]
        common_metric_names = set(all_metric_names[0])
        for m in all_metric_names[1:]:
            common_metric_names.intersection_update(m)
        metric_names = sorted(common_metric_names)

        output_names = results[0].metadata.report["measured_output_names"]

        # TODO put nominal values in dedicated group
        data = defaultdict(list)
        for result in results:
            for name, value in result.nominal_data.items():
                # data is then converted to dataframe.
                # arrays are stringified because they could be of different lengths
                if isinstance(value, ndarray) and value.size > 1:
                    value = str(value)
                data[f"{name}[{IODataset.INPUT_GROUP}]"].append(value)
            for metric_name in metric_names:
                for name, value in result.integrated_metrics[metric_name].items():
                    data[f"{name}[{metric_name}]"].append(value)
            reference_outputs = result.measured_data.get_view(
                group_names=[IODataset.OUTPUT_GROUP]
            ).copy()
            reference_outputs.columns = reference_outputs.get_columns(as_tuple=False)
            reference_outputs = reference_outputs.mean().to_dict()
            for name, value in reference_outputs.items():
                data[f"{name}[Reference]"] = value
            simulated_outputs = result.simulated_data.get_view(
                group_names=[IODataset.OUTPUT_GROUP]
            ).copy()
            simulated_outputs.columns = simulated_outputs.get_columns(as_tuple=False)
            simulated_outputs = simulated_outputs.mean().to_dict()
            for name, value in simulated_outputs.items():
                data[f"{name}[{IODataset.OUTPUT_GROUP}]"] = value

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
                self.integrated_metrics[metric_name][output_name] = (
                    mean_metric.compute(
                        self.element_wise_metric.get_view(
                            group_names=[f"{IODataset.OUTPUT_GROUP}"],
                            variable_names=[output_name],
                        ),
                        self.element_wise_metric.get_view(
                            group_names=["Reference"],
                            variable_names=[output_name],
                        )
                    )
                )


        # TODO Compute the integrated metrics