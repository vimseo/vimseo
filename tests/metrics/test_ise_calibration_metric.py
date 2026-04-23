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

from typing import TYPE_CHECKING

import pytest
from gemseo.datasets.dataset import Dataset
from numpy import concatenate
from numpy import linspace
from numpy import ones

from vimseo.tools.calibration.calibration_metrics import SBPISE
from vimseo.utilities.curves_generator import expressions_convexity
from vimseo.utilities.curves_generator import expressions_oscillate
from vimseo.utilities.curves_generator import get_history

if TYPE_CHECKING:
    from numpy import ndarray


N_POINTS = 10
X_LEFT = -0.5
X_RIGHT = 0.5
DELTA_Y = 0.05


def _swap_points(x: ndarray, y: ndarray):
    """Swap two points in the curve defined by x and y."""
    idx1 = 0
    idx2 = 1
    x[idx1], x[idx2] = x[idx2], x[idx1]
    y[idx1], y[idx2] = y[idx2], y[idx1]


@pytest.mark.parametrize(
    ("weight_left", "weight_right"),
    [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.0, 1.0),
    ],
)
@pytest.mark.parametrize(
    "is_decreasing_simulation",
    [False, True],
)
@pytest.mark.parametrize(
    "is_decreasing_reference",
    [False, True],
)
@pytest.mark.parametrize(
    ("x_left", "x_right"),
    [
        (X_LEFT, X_RIGHT),
        (X_LEFT - 0.1, X_RIGHT + 0.1),
        (X_LEFT + 0.1, X_RIGHT - 0.1),
    ],
)
@pytest.mark.parametrize(
    "swap_points",
    [
        True,
        False,
    ],
)
def test_ise(
    weight_left,
    weight_right,
    x_left,
    x_right,
    is_decreasing_reference,
    is_decreasing_simulation,
    swap_points,
):
    metric = SBPISE("y", "y_mesh", True, weight_left, weight_right)

    # building a mock reference curve
    x_hist_exp = linspace(x_left, x_right, N_POINTS)
    y_hist_exp = ones(x_hist_exp.shape)

    # building a mock numerical curve
    x_hist_num = linspace(X_LEFT, X_RIGHT, N_POINTS)
    y_hist_num = ones(x_hist_num.shape) * (1.0 + DELTA_Y)

    if is_decreasing_reference:
        x_hist_exp = x_hist_exp[::-1]
        y_hist_exp = y_hist_exp[::-1]
    if is_decreasing_simulation:
        x_hist_num = x_hist_num[::-1]
        y_hist_num = y_hist_num[::-1]

    if swap_points:
        _swap_points(x_hist_exp, y_hist_exp)
        _swap_points(x_hist_num, y_hist_num)

    reference_data = Dataset.from_array(
        data=[concatenate([x_hist_exp, y_hist_exp])],
        variable_names=["y_mesh", "y"],
        variable_names_to_n_components={
            "y": N_POINTS,
            "y_mesh": N_POINTS,
        },
    )
    model_dataset = Dataset.from_array(
        data=[concatenate([x_hist_num, y_hist_num])],
        variable_names=["y_mesh", "y"],
        variable_names_to_n_components={
            "y": N_POINTS,
            "y_mesh": N_POINTS,
        },
    )

    metric.set_reference_data(reference_data.to_dict_of_arrays(False))
    result = metric._evaluate_measure(model_dataset.to_dict_of_arrays(False))

    common_support = min(x_right - x_left, X_RIGHT - X_LEFT)
    if weight_left == 0.0 and weight_right == 0.0:
        assert result == pytest.approx(common_support * DELTA_Y**2)
    elif weight_left == 0.0 and weight_right == 1.0:
        assert result == pytest.approx(
            0.5 * common_support * DELTA_Y**2 + 0.5 * (x_right - X_RIGHT) ** 2
        )
    elif weight_left == 1.0 and weight_right == 0.0:
        assert result == pytest.approx(
            0.5 * common_support * DELTA_Y**2 + 0.5 * (X_LEFT - x_left) ** 2
        )
    else:
        msg = "Invalid weight combination"
        raise ValueError(msg)


@pytest.mark.parametrize(
    ("x_left", "x_right"),
    [
        (-0.2, -0.1),
        (1.1, 1.2),
    ],
)
def test_ise_disjoint_supports(x_left, x_right):
    metric = SBPISE("y", "y_mesh", True, 1.0, 1.0)

    x_hist_exp = linspace(x_left, x_right, N_POINTS)
    y_hist_exp = get_history(
        [
            expressions_convexity["convex"],
            expressions_oscillate["half_drop"],
            "x*0.9",
        ],
        nb_points=N_POINTS,
        support=x_hist_exp,
    )

    # building a mock numerical curve
    x_hist_num = linspace(0.0, 1.0, N_POINTS)
    y_hist_num = get_history(
        list_expressions=[
            expressions_convexity["concave"],
            expressions_oscillate["half_drop"],
        ],
        nb_points=N_POINTS,
        support=x_hist_num,
    )

    reference_data = Dataset.from_array(
        data=[concatenate([x_hist_exp, y_hist_exp])],
        variable_names=["y_mesh", "y"],
        variable_names_to_n_components={
            "y": N_POINTS,
            "y_mesh": N_POINTS,
        },
    )
    model_dataset = Dataset.from_array(
        data=[concatenate([x_hist_num, y_hist_num])],
        variable_names=["y_mesh", "y"],
        variable_names_to_n_components={
            "y": N_POINTS,
            "y_mesh": N_POINTS,
        },
    )

    metric.set_reference_data(reference_data.to_dict_of_arrays(False))

    with pytest.raises(ValueError):
        metric._evaluate_measure(model_dataset.to_dict_of_arrays(False))
