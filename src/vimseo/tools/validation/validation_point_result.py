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
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING

from gemseo.utils.string_tools import MultiLineString

from vimseo.tools.base_tool import BaseResult
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Mapping

    from gemseo.datasets.dataset import Dataset
    from numpy import ndarray

LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationPointResult(BaseResult):
    """The result of a validation point."""

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
