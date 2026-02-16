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
from numpy import ndarray
from pandas import DataFrame

from vimseo.tools.base_tool import BaseResult
from vimseo.utilities.datasets import dataframe_to_dataset

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from vimseo.tools.validation.validation_point_result import ValidationPointResult

LOGGER = logging.getLogger(__name__)


class StochasticValidationCaseResult(BaseResult):
    """The result of a validation case."""

    validation_point_results: Iterable[ValidationPointResult] = ()
    """A list of validation point results."""

    def to_dataframe(self, metric_name: str):
        """Return a ``Pandas.DataFrame`` containing on each row the nominal inputs and
        the integrated metrics as outputs of each ``ValidationPointResult``.

        Args:
            metric_name: The name of the metric to export.
        """
        data = defaultdict(list)
        for result in self.validation_point_results:
            for name, value in result.nominal_data.items():
                # data is then converted to dataframe.
                # arrays are stringified because they could be of different lengths
                if isinstance(value, ndarray) and value.size > 1:
                    value = str(value)
                data[name].append(value)
            for name, value in result.integrated_metrics[metric_name].items():
                data[f"{metric_name}[{name}]"].append(value)
        return DataFrame.from_dict(data)


# TODO rename into ValidationCaseResult
class DeterministicValidationCaseResult(BaseResult):
    """The result of a deterministic validation."""

    element_wise_metrics: IODataset | None = field(default_factory=None)

    integrated_metrics: Mapping[str, Mapping[str, float]] | None = None
    """A dictionary mapping variable names and metric names to integrated metric values
    corresponding the each validation point (i.e. each sample of the reference data)."""

    def set_from_point_results(self, results: Iterable[ValidationPointResult]):

        # TODO compute the list of common metric names. Use the result.metadata.settings["metric_names"]
        metric_names = []

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

        # TODO Compute the integrated metrics