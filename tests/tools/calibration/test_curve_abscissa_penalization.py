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

from typing import TYPE_CHECKING

import pytest
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings import NLOPT_COBYLA_Settings
from gemseo.datasets.io_dataset import IODataset
from gemseo.post.hessian_history import np_min
from gemseo_calibration.measures.integrated_measure import CurveScaling
from numpy import concatenate
from numpy import linspace
from numpy import max as np_max

from vimseo.api import activate_logger
from vimseo.tools.calibration.calibration_step import CalibrationMetricSettings
from vimseo.tools.calibration.calibration_step import CalibrationStep
from vimseo.tools.calibration.calibration_step import CalibrationStepInputs
from vimseo.tools.calibration.calibration_step import CalibrationStepSettings
from vimseo.utilities.curves_generator import expressions_convexity
from vimseo.utilities.curves_generator import expressions_oscillate
from vimseo.utilities.curves_generator import get_history

if TYPE_CHECKING:
    from gemseo.algos.opt.base_optimizer_settings import BaseOptimizerSettings

activate_logger()

NB_REF_POINTS = 50  # The number of points in the reference curve.
NB_ITER = 50  # The number of iterations for the optimization.
X0_BOUND_REL_SHIFT = (
    0.05  # The relative shift of the starting point of the optimization
)
# compared to the reference curve.
# It is used to test the penalization of exceeding the abscissa range.
# For example, if X0_BOUND_REL_SHIFT is 0.05, then the starting point for x_left will be
# 5% smaller than x_ref_left and the starting point for x_right will be 5% larger than
# x_ref_right. This means that the starting point will be outside the range defined
# by x_ref_left and x_ref_right, which should trigger the penalization of exceeding
# the abscissa range.


def create_reference_dataset(
    x_left: float, x_right: float, y_max: float = 1.0
) -> IODataset:
    """Creates a reference dataset for the test.

    The reference curve is generated using the expressions defined in the curve
    generator utilities. The curve is defined on the range [x_left, x_right]
    and is scaled so that its maximum y value is y_max."""

    x_ref = get_history(support=linspace(x_left, x_right, NB_REF_POINTS))
    y_ref = get_history(
        list_expressions=[
            expressions_convexity["convex"],
            expressions_oscillate["half_drop"],
        ],
        support=x_ref,
    )
    y_ref = y_max * y_ref / (np_max(y_ref) - np_min(y_ref))
    reference_data = IODataset.from_array(
        data=[concatenate([x_ref, y_ref])],
        variable_names=["y_axis", "y"],
        variable_names_to_n_components={
            "y": NB_REF_POINTS,
            "y_axis": NB_REF_POINTS,
        },
    )
    reference_data.add_variable(
        variable_name="x_left", data=[x_left], group_name="outputs"
    )
    reference_data.add_variable(
        variable_name="x_right", data=[x_right], group_name="outputs"
    )
    return reference_data


def check_abscissa_bound_penalization(
    x_ref_left: float,
    x_ref_right: float,
    y_ref_max: float,
    delta_x_left: float,
    delta_x_right: float,
    algo: str,
    optimizer_settings: BaseOptimizerSettings,
) -> None:
    """Checks the penalization for exceeding the abscissa bounds.

    The penalization is computed as the sum of the penalization for exceeding
    the left bound and the penalization for exceeding the right bound. The
    penalization for exceeding a bound is computed as the product of the
    penalization factor and the distance between the point and the bound."""

    reference_data = create_reference_dataset(x_ref_left, x_ref_right, y_ref_max)

    # The starting point of the model x left and x right:
    x_left = x_ref_left * (1 + delta_x_left)
    x_right = x_ref_right * (1 + delta_x_right)
    # The starting point for the max y of the model:
    y_max = 1.2 * reference_data.get_view(variable_names=["y"]).to_numpy().max()

    design_space = DesignSpace()
    design_space.add_variable(
        "x_left", value=x_left, lower_bound=x_left * 1.5, upper_bound=x_left * 0.5
    )
    design_space.add_variable(
        "x_right", value=x_right, lower_bound=x_right * 0.5, upper_bound=x_right * 1.5
    )
    design_space.add_variable(
        "y_max", value=y_max, lower_bound=0.5 * y_max, upper_bound=2 * y_max
    )

    step = CalibrationStep()
    step.execute(
        inputs=CalibrationStepInputs(
            reference_data={
                "Dummy": reference_data,
            },
            starting_point={"x_left": x_left, "x_right": x_right, "y_max": y_max},
            design_space=design_space,
        ),
        settings=CalibrationStepSettings(
            name_to_models={"Dummy": "MockCurvesXRange"},
            control_outputs={
                "y": CalibrationMetricSettings(
                    measure="SBPISE",
                    mesh="y_axis",
                    scaling=CurveScaling.XYRange,
                    x_left_penalization_factor=1.0,
                    x_right_penalization_factor=1.0,
                ),
            },
            parameter_names=["x_left", "x_right", "y_max"],
            optimizer_name=algo,
            optimizer_settings=optimizer_settings,
        ),
    )
    # step.plot_results(step.result, show=False, save=True)
    assert step.result.posterior_parameters["x_left"] == pytest.approx(
        x_ref_left, rel=5e-2
    )
    assert step.result.posterior_parameters["x_right"] == pytest.approx(
        x_ref_right, rel=5e-2
    )
    assert step.result.posterior_parameters["y_max"] == pytest.approx(
        y_ref_max, rel=5e-2
    )


@pytest.mark.parametrize(
    ("x_ref_left", "x_ref_right", "y_ref_max"),
    [
        (-0.5, 0.5, 1.0),
    ],
)
@pytest.mark.parametrize(
    ("algo", "optimizer_settings", "delta_x_left", "delta_x_right"),
    [
        (
            "NLOPT_COBYLA",
            NLOPT_COBYLA_Settings(max_iter=50),
            -X0_BOUND_REL_SHIFT,
            X0_BOUND_REL_SHIFT,
        ),
    ],
)
def test_abscissa_bound_penalization_nominal_case(
    tmp_wd,
    algo,
    optimizer_settings,
    delta_x_left,
    delta_x_right,
    x_ref_left,
    x_ref_right,
    y_ref_max,
):
    """Checks that the penalization for unmatched abscissa bounds is working as expected."""
    check_abscissa_bound_penalization(
        x_ref_left=x_ref_left,
        x_ref_right=x_ref_right,
        y_ref_max=y_ref_max,
        delta_x_left=delta_x_left,
        delta_x_right=delta_x_right,
        algo=algo,
        optimizer_settings=optimizer_settings,
    )


@pytest.mark.slow
@pytest.mark.parametrize(
    ("x_ref_left", "x_ref_right", "y_ref_max"),
    [
        (-5e-4, 5e-4, 1.0),
        (-0.5, 0.5, 1e-3),
        (-5e-4, 5e-4, 1e-3),
    ],
)
@pytest.mark.parametrize(
    ("algo", "optimizer_settings", "delta_x_left", "delta_x_right"),
    [
        (
            "NLOPT_COBYLA",
            NLOPT_COBYLA_Settings(max_iter=50),
            X0_BOUND_REL_SHIFT,
            X0_BOUND_REL_SHIFT,
        ),
        (
            "NLOPT_COBYLA",
            NLOPT_COBYLA_Settings(max_iter=50),
            -X0_BOUND_REL_SHIFT,
            -X0_BOUND_REL_SHIFT,
        ),
        (
            "NLOPT_COBYLA",
            NLOPT_COBYLA_Settings(max_iter=50),
            X0_BOUND_REL_SHIFT,
            -X0_BOUND_REL_SHIFT,
        ),
    ],
)
def test_abscissa_bound_penalization_all_cases(
    tmp_wd,
    algo,
    optimizer_settings,
    delta_x_left,
    delta_x_right,
    x_ref_left,
    x_ref_right,
    y_ref_max,
):
    """Checks that the penalization for unmatched abscissa bounds is working as expected."""
    check_abscissa_bound_penalization(
        x_ref_left=x_ref_left,
        x_ref_right=x_ref_right,
        y_ref_max=y_ref_max,
        delta_x_left=delta_x_left,
        delta_x_right=delta_x_right,
        algo=algo,
        optimizer_settings=optimizer_settings,
    )
