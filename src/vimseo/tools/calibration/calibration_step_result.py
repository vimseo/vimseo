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

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field

from gemseo.algos.design_space import DesignSpace
from numpy import ndarray
from pandas import DataFrame
from plotly.graph_objs import Figure

from vimseo.tools.base_result import BaseResult

CurveDataType = Mapping[str, list[Mapping[str, DataFrame]]]


@dataclass
class CurveData:
    posterior_dataframes: CurveDataType | None = None

    prior_dataframes: CurveDataType | None = None

    reference_dataframes: CurveDataType | None = None


@dataclass
class CalibrationStepResult(BaseResult):
    """The result of a calibration step."""

    posterior_parameters: Mapping[str, ndarray] | None = field(
        default=None, metadata="The calibrated parameters."
    )

    prior_parameters: Mapping[str, ndarray] | None = None

    reference_data: Mapping[str, ndarray] | None = None

    design_space: DesignSpace | None = None

    prior_model_data: Mapping[str, ndarray] | None = None

    posterior_model_data: Mapping[str, ndarray] | None = None

    metric_variables: Mapping[str, tuple[str]] | None = None

    post_processing_figures: Mapping[str, Figure] | None = field(
        default=None,
        metadata="The figures showing the optimization convergence history.",
    )

    curve_data: Iterable[CurveDataType | None] = field(default_factory=CurveData)

    objective: str = ""
