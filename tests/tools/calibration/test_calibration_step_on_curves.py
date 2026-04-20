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

import pytest
from gemseo_calibration.calibrator import CalibrationMetricSettings
from numpy import atleast_1d

from vimseo.api import create_model
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.calibration.calibration_step import CalibrationStep
from vimseo.tools.calibration.calibration_step import CalibrationStepInputs
from vimseo.tools.calibration.calibration_step import CalibrationStepSettings
from vimseo.tools.calibration.calibration_step_result import CalibrationStepResult
from vimseo.tools.calibration.input_data import CALIBRATION_INPUT_DATA
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_parameter_space,
)


def calibration_on_curves(mesh: str):
    x_target = 1.5
    reference_mock_curves = create_model("MockCurves", "Dummy")
    reference_mock_curves.default_input_data["x"] = atleast_1d(x_target)
    reference_mock_curves.cache = None
    reference_data = generate_reference_from_parameter_space(
        reference_mock_curves,
        SpaceToolFileIO()
        .read(CALIBRATION_INPUT_DATA / "experimental_space_mock_curves.json")
        .parameter_space,
        n_samples=6,
        as_dataset=True,
    )

    output_name = "y"

    step = CalibrationStep()
    step.execute(
        inputs=CalibrationStepInputs(
            reference_data={
                "Dummy": reference_data,
            },
        ),
        settings=CalibrationStepSettings(
            model_name={"Dummy": "MockCurves"},
            control_outputs={
                output_name: CalibrationMetricSettings(
                    measure="SBPISE", mesh=mesh
                ).model_dump()
            },
            input_names=[
                "x_1",
            ],
            parameter_names=["x"],
        ),
    )

    return step, x_target


def test_calibration_on_curves(tmp_wd):
    """Check that a calibration step based on curves can be executed."""
    calibration_step, x_target = calibration_on_curves("y_axis")
    calibration_step.plot_results(calibration_step.result, show=False, save=True)
    assert calibration_step.result.posterior_parameters["x"] == pytest.approx(x_target)


def test_plots_on_curves(tmp_wd):
    """Check that a calibration step based on curves can be plotted."""
    calibration_step, _ = calibration_on_curves("y_axis")
    calibration_step.plot_results(calibration_step.result, show=False, save=True)
    assert (
        calibration_step.working_directory
        / "simulated_versus_reference_dplt_load_case_Cantilever.png"
    )
    assert (
        calibration_step.working_directory
        / "simulated_versus_reference_dplt_versus_dplt_grid_load_case_Cantilever.html"
    )


def test_calibration_default_axis(tmp_wd):
    """Check that a calibration step based on curves can be executed with the default axis."""
    calibration_step, x_target = calibration_on_curves("")
    calibration_step.plot_results(calibration_step.result, show=False, save=True)
    assert calibration_step.result.posterior_parameters["x"] == pytest.approx(x_target)


def test_serialization(tmp_wd):
    """Check that a CalibrationStepResult can be serialized to hdf5."""
    calibration_step, _ = calibration_on_curves("")
    result = calibration_step.result
    result.to_hdf5("result.hdf5")
    serialized_result = CalibrationStepResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)
