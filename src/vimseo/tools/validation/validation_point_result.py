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
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.string_tools import MultiLineString
from numpy import ndarray
from pydantic import Field

from vimseo.tools.base_tool import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import create_figure
from vimseo.tools.result_visualization import flatten_numbers
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.tools.result_visualization import Figure

LOGGER = logging.getLogger(__name__)


class ValidationPointVisualizationSettings(BaseVisualizationSettings):
    output_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the outputs whose simulated and measured "
        "distributions are compared. If empty, use all the measured outputs.",
    )


@dataclass
class ValidationPointResult(BaseResult):
    """The result of a validation point."""

    _VISUALIZATION_SETTINGS: ClassVar[type[ValidationPointVisualizationSettings]] = (
        ValidationPointVisualizationSettings
    )

    nominal_data: Mapping[str, float | int | ndarray] | None = None

    measured_data: Dataset | None = None
    """The dataset containing the reference measured data."""

    simulated_data: Dataset | None = None
    """The dataset containing simulated results."""

    sample_to_sample_error: Dataset | None = None
    """The dataset containing the sample to sample errors."""

    integrated_metrics: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    """A dictionary mapping variable names and metric names to integrated metric
    values."""

    def __str__(self):
        text = MultiLineString()
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        text.add("Integrated metrics:")
        text.indent()
        for k, v in self.integrated_metrics.items():
            text.add(f"{k}: {v}")
        text.dedent()
        text.add("")
        text.add("Sample to sample error:")
        text.add(repr(self.sample_to_sample_error))
        text.add("")
        text.add("Measured data:")
        text.add(repr(self.measured_data))
        text.add("")
        text.add("Simulated data:")
        text.add(repr(self.simulated_data))
        return str(text)

    def get_output_names(self) -> list[str]:
        """Return the names of the outputs compared to measured data."""
        names = self.metadata.report.get("measured_output_names")
        if names:
            return list(names)
        if self.simulated_data is None:
            return []
        return self.simulated_data.get_variable_names(IODataset.OUTPUT_GROUP)

    def _create_figures(
        self, settings: ValidationPointVisualizationSettings
    ) -> dict[str, Figure]:
        if self.measured_data is None or self.simulated_data is None:
            return {}

        from statsmodels.graphics.gofplots import qqplot_2samples

        from vimseo.tools.post_tools.distribution_comparison_plot import (
            DistributionComparison,
        )

        figures = {}
        for output_name in settings.output_names or self.get_output_names():
            for comparison_type in ["PDF", "CDF"]:
                figures[f"{comparison_type}_comparison_{output_name}"] = create_figure(
                    DistributionComparison,
                    self,
                    output_name,
                    comparison_type,
                    show_type_b_uncertainties=True,
                )

            figures[f"qq_plot_{output_name}"] = qqplot_2samples(
                self.measured_data.to_dict_of_arrays(by_group=False)[
                    output_name
                ].ravel(),
                self.simulated_data.to_dict_of_arrays(by_group=False)[
                    output_name
                ].ravel(),
                ylabel="Simulated",
                xlabel="Reference",
                line="45",
            )
        return figures

    def get_key_values(self) -> dict[str, float]:
        return flatten_numbers(self.integrated_metrics or {})
