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
from datetime import datetime
from typing import TYPE_CHECKING

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from gemseo_calibration.measures.integrated_measure import CurveScaling
from gemseo_calibration.measures.integrated_measure import IntegratedMeasure
from gemseo_calibration.measures.mean_measure import MeanMeasure
from gemseo_calibration.measures.mse import MSE
from numpy import abs as np_abs
from numpy import argsort
from numpy import array
from numpy import atleast_1d
from numpy import linspace
from numpy import max as np_max
from numpy import mean
from numpy import min as np_min
from numpy import sum as np_sum
from numpy import union1d
from scipy.integrate import trapezoid
from scipy.interpolate import interp1d

if TYPE_CHECKING:
    from gemseo.typing import RealArray
    from gemseo_calibration.measure import DataType
    from numpy import ndarray

LOGGER = logging.getLogger(__name__)

EPSILON = 1e-12


def _sort_and_align(x, y):
    """Sort x (and y accordingly), ensuring x is increasing."""
    idx = argsort(x)
    return x[idx], y[idx]


def _restrict_to_range(x, y, x_min, x_max):
    """Restrict (x, y) to the range [x_min, x_max]."""
    mask = (x >= x_min) & (x <= x_max)
    return x[mask], y[mask]


def _scale_xy(x, y, x0, y0, factor_x, factor_y):
    return (x - x0) * factor_x, (y - y0) * factor_y


class RelativeMSE(MeanMeasure):
    """The mean square error between the model and reference output data."""

    @staticmethod
    def _compare_data(data: RealArray, other_data: RealArray) -> RealArray:
        """

        Args:
            data: The reference data.
            other_data: The model data.

        Returns: The metric value.

        """
        metric = ((data - other_data) / (data + EPSILON)) ** 2
        LOGGER.warning(f"Relative MSE: {metric}")
        return metric


class SBPISE(IntegratedMeasure):
    """An Integrated Square Error metric with scaling of the curves and bound
    penalization."""

    PLOT = False

    def _evaluate_measure(self, model_dataset: DataType) -> float:  # noqa: D102
        model_data = model_dataset[self.output_name]
        model_mesh = (
            model_dataset[self.mesh_name]
            if self.mesh_name != ""
            else [
                linspace(0.0, 1.0, len(model_data[0])) for i in range(len(model_data))
            ]
        )
        compared_data = []
        x_refs = []
        exceeding_start_metrics = []
        exceeding_end_metrics = []
        if self.PLOT:
            _fig, ax = plt.subplots()
        for i in range(len(model_data)):
            x_ref = self.reference_mesh[i]
            y_ref = self._reference_data[i]
            x_i = model_mesh[i]
            y_i = model_data[i]

            x_ref, y_ref = _sort_and_align(x_ref, y_ref)
            x_i, y_i = _sort_and_align(x_i, y_i)

            # Validate
            if x_ref[-1] <= x_i[0] or x_ref[0] >= x_i[-1]:
                msg = "Reference and model x-axis are disjoint."
                raise ValueError(msg)
            if x_i[-1] == x_i[0]:
                msg = "Model x-axis is a point."
                raise ValueError(msg)
            if x_ref[-1] == x_ref[0]:
                msg = "Reference x-axis is a point."
                raise ValueError(msg)

            # Scale
            if self._scaling == CurveScaling.XYRange:
                x0, y0 = mean(x_ref), mean(y_ref)
                factor_x = 1.0 / max(x_ref[-1] - x_ref[0], x_i[-1] - x_i[0])
                delta_y = max(np_max(y_ref) - np_min(y_ref), np_max(y_i) - np_min(y_i))
                factor_y = 1.0 / EPSILON if delta_y < EPSILON else 1.0 / delta_y
                x_ref, y_ref = _scale_xy(x_ref, y_ref, x0, y0, factor_x, factor_y)
                x_i, y_i = _scale_xy(x_i, y_i, x0, y0, factor_x, factor_y)

            y_i_raw = y_i.copy()

            # Exceeding areas
            delta_x_left = abs(x_i[0] - x_ref[0])
            delta_x_right = abs(x_ref[-1] - x_i[-1])
            exceeding_area = (
                (delta_x_left + delta_x_right)
                * 0.5
                * (np_max(np_abs(y_ref)) + np_max(np_abs(y_i)))
            )

            for name, value in [("x_left", delta_x_left), ("x_right", delta_x_right)]:
                mse = MSE(output_name=name)
                mse.set_reference_data({name: atleast_1d(0.0)})
                metric = mse._evaluate_measure({name: atleast_1d(value)})
                (
                    exceeding_start_metrics
                    if name == "x_left"
                    else exceeding_end_metrics
                ).append(metric)

            # Align x-axes: add x_i points inside x_ref range, interpolate y_ref on them
            x_i_in_x_ref = x_i[(x_i >= x_ref[0]) & (x_i <= x_ref[-1])]
            interpolator = interp1d(x_ref, y_ref)
            x_ref = union1d(x_ref, x_i_in_x_ref)
            y_ref = interpolator(x_ref)  # re-interpolate after union

            # Restrict x_ref to x_i range
            x_ref, y_ref = _restrict_to_range(x_ref, y_ref, x_i[0], x_i[-1])

            # Interpolate y_i on the new x_ref grid
            y_i = interp1d(x_i, y_i, assume_sorted=True, bounds_error=True)(x_ref)

            compared_data.append(self._compare_data(y_ref, y_i))
            x_refs.append(x_ref)

            if self.PLOT:
                ax.plot(
                    x_ref,
                    y_i,
                    "b-*",
                    label=f"model data interpolated on ref sample {i}",
                )
                ax.plot(x_i, y_i_raw, "r--+", label=f"raw model data {i}")
                ax.plot(x_ref, y_ref, "k-o", label=f"ref sample {i}")
                height = (
                    0.0
                    if abs(exceeding_area) < 1e-12
                    else exceeding_area / (delta_x_right + delta_x_left)
                )
                rect_start = patches.Rectangle(
                    (x_ref[0], 0.0),
                    -delta_x_left,
                    height,
                    edgecolor="r",
                    facecolor="none",
                )
                rect_end = patches.Rectangle(
                    (x_ref[-1], 0.0),
                    delta_x_right,
                    height,
                    edgecolor="r",
                    facecolor="none",
                )
                ax.add_patch(rect_start)
                ax.add_patch(rect_end)

            LOGGER.warning(
                f"Metrics on scaled curves for variable {self.output_name}:\n"
                f"MSE mismatch x-axis left bound: {exceeding_start_metrics[-1]}\n"
                f"MSE mismatch x-axis right bound: {exceeding_end_metrics[-1]}\n"
                f"Area metric: {trapezoid(compared_data[-1], x_ref)}\n"
                f"(model_support_length - reference_support_length) / model_support_length = "
                f"{(delta_x_left + delta_x_right) / abs(x_i[-1] - x_i[0])}\n"
            )  # noqa: T201

        if self.PLOT:
            plt.legend()
            plt.savefig(
                f"{self.mesh_name}_{self.output_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png".replace(
                    ":", "_"
                )
            )

        weights = array([
            self._x_left_penalization_factor,
            1.0,
            self._x_right_penalization_factor,
        ])
        weights /= np_sum(weights)

        metric = mean([
            weights[1]
            * (
                trapezoid(
                    data,
                    x_ref,
                )
            )
            + weights[0] * exceeding_start_metric
            + weights[2] * exceeding_end_metric
            for x_ref, data, exceeding_start_metric, exceeding_end_metric in zip(
                x_refs,
                compared_data,
                exceeding_start_metrics,
                exceeding_end_metrics,
                strict=False,
            )
        ])
        LOGGER.warning(
            f"{self.__class__.__name__} metric for variable {self.output_name}: {metric}\n"
            f"Weights (left, area, right): ({weights})."
        )  # noqa: T201
        return metric

    @staticmethod
    def _compare_data(data: ndarray, other_data: ndarray) -> ndarray:
        return (data - other_data) ** 2
