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

import collections.abc

import pytest
from gemseo_calibration.calibrator import CalibrationMetricSettings
from numpy import atleast_1d
from numpy import ndarray

from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.calibration.calibration_step import CalibrationStep
from vimseo.tools.calibration.calibration_step import CalibrationStepInputs
from vimseo.tools.calibration.calibration_step import CalibrationStepSettings
from vimseo.tools.calibration.calibration_step import MetricVariable
from vimseo.tools.calibration.calibration_step_result import CalibrationStepResult
from vimseo.tools.calibration.input_data import CALIBRATION_INPUT_DATA
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_parameter_space,
)
from vimseo.utilities.model_data import MetricVariableType

TARGET_YOUNG_MODULUS = 2.2e5


@pytest.fixture
def calibration_on_scalars():
    space_tool_result = SpaceToolFileIO().read(
        CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
    )
    target_model = create_model("BendingTestAnalytical", "Cantilever")
    target_model.EXTRA_INPUT_GRAMMAR_CHECK = True
    target_model.default_input_data["young_modulus"] = atleast_1d(TARGET_YOUNG_MODULUS)
    target_model.cache = None
    reference_dataset_cantilever = generate_reference_from_parameter_space(
        target_model, space_tool_result.parameter_space, n_samples=6, as_dataset=True
    )

    output_name = "reaction_forces"

    step = CalibrationStep()
    step.execute(
        inputs=CalibrationStepInputs(
            reference_data={
                "Cantilever": reference_dataset_cantilever,
            },
        ),
        settings=CalibrationStepSettings(
            name_to_models={"Cantilever": "BendingTestAnalytical"},
            control_outputs={output_name: CalibrationMetricSettings(measure="MSE")},
            input_names=[
                "height",
                "width",
                "imposed_dplt",
            ],
            parameter_names=["young_modulus"],
        ),
    )

    return step, target_model


def test_calibration_step_no_starting_point(tmp_wd):
    space_tool_result = SpaceToolFileIO().read(
        CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
    )
    target_model = create_model("BendingTestAnalytical", "Cantilever")
    target_model.EXTRA_INPUT_GRAMMAR_CHECK = True
    target_model.default_input_data["young_modulus"] = atleast_1d(TARGET_YOUNG_MODULUS)
    target_model.cache = None
    reference_dataset_cantilever = generate_reference_from_parameter_space(
        target_model,
        space_tool_result.parameter_space,
        n_samples=6,
        as_dataset=True,
    )

    step = CalibrationStep()
    step.execute(
        inputs=CalibrationStepInputs(
            reference_data={
                "Cantilever": reference_dataset_cantilever,
            },
        ),
        settings=CalibrationStepSettings(
            name_to_models={"Cantilever": "BendingTestAnalytical"},
            control_outputs={
                "reaction_forces": CalibrationMetricSettings(measure="MSE")
            },
            input_names=[
                "height",
                "width",
                "imposed_dplt",
            ],
            parameter_names=["young_modulus"],
        ),
    )

    assert (
        step.result.prior_parameters["young_modulus"]
        == create_model("BendingTestAnalytical", "Cantilever").default_input_data[
            "young_modulus"
        ][0]
    )
    assert list(step.result.prior_parameters.keys()) == ["young_modulus"]

    assert step.result.posterior_parameters["young_modulus"] == pytest.approx(
        TARGET_YOUNG_MODULUS, rel=1e-2
    )


def test_calibration_step_with_starting_point(tmp_wd):
    space_tool_result = SpaceToolFileIO().read(
        CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
    )
    target_model = create_model("BendingTestAnalytical", "Cantilever")
    target_model.EXTRA_INPUT_GRAMMAR_CHECK = True
    target_model.default_input_data["young_modulus"] = atleast_1d(TARGET_YOUNG_MODULUS)
    target_model.cache = None
    reference_dataset_cantilever = generate_reference_from_parameter_space(
        target_model, space_tool_result.parameter_space, n_samples=6, as_dataset=True
    )

    step = CalibrationStep()
    step.execute(
        inputs=CalibrationStepInputs(
            reference_data={
                "Cantilever": reference_dataset_cantilever,
            },
            starting_point={
                "young_modulus": atleast_1d(2e5),
                "nu_p": atleast_1d(0.35),
            },
        ),
        settings=CalibrationStepSettings(
            name_to_models={"Cantilever": "BendingTestAnalytical"},
            control_outputs={
                "reaction_forces": CalibrationMetricSettings(measure="MSE")
            },
            input_names=[
                "height",
                "width",
                "imposed_dplt",
            ],
            parameter_names=["young_modulus"],
        ),
    )

    assert step.result.prior_parameters["young_modulus"] == 2e5
    assert step.result.posterior_parameters["young_modulus"] == pytest.approx(
        TARGET_YOUNG_MODULUS, rel=1e-2
    )
    for value in step.result.posterior_parameters.values():
        assert not (
            isinstance(value, (collections.abc.Sequence, ndarray)) and len(value) == 1
        )


def test_calibration_step_on_scalars_single_model(tmp_wd, calibration_on_scalars):
    """Check that a calibration step runs correctly on a single load case.

    The design space is defined from a starting point and model input bounds.
    """
    output_name = "reaction_forces"
    calibration_step, target_model = calibration_on_scalars
    assert calibration_step.result.metric_variables == [
        MetricVariable(
            "Cantilever:reaction_forces",
            MetricVariableType.SCALAR,
        )
    ]
    assert calibration_step.result.objective == f"MSE[Cantilever:{output_name}]"
    # design space values are modified by the optimizer. So it seems that we cannot
    # easily
    # check the initial values.
    # If we set the settings at construction, then we could check it before executing
    # the tool.
    assert calibration_step.result.design_space.get_current_value(["young_modulus"])[
        0
    ] == pytest.approx(TARGET_YOUNG_MODULUS, rel=1e-2)
    assert calibration_step.result.posterior_parameters[
        "young_modulus"
    ] == pytest.approx(TARGET_YOUNG_MODULUS, rel=1e-2)
    model_bis = create_model(
        "BendingTestAnalytical",
        "Cantilever",
        **IntegratedModelSettings(
            cache_file_path="BendingTestAnalytical_Beam_Cantilever_bis_cache.hdf"
        ).model_dump(),
    )
    assert model_bis.execute({
        k: atleast_1d(v)
        for k, v in calibration_step.result.posterior_parameters.items()
    })[f"{output_name}"] == pytest.approx(target_model.execute()[output_name], rel=0.01)


def test_calibration_step_on_scalars_multiple_models(tmp_wd):
    """Check that a calibration step runs correctly, when the design space is left to
    default.

    The design space is defined from previously calibrated parameters and model
    information.
    """
    # The reference data is generated from two different Young modulus, such that
    # the coupled calibration has to find the best compromise between the two values:
    target_young_modulus_cantilever = 2e5
    target_young_modulus_three_points = 2.3e5

    space_tool_result = SpaceToolFileIO().read(
        CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
    )
    target_model = create_model("BendingTestAnalytical", "Cantilever")
    target_model.EXTRA_INPUT_GRAMMAR_CHECK = True
    target_model.default_input_data["young_modulus"] = atleast_1d(
        target_young_modulus_cantilever
    )
    target_model.cache = None
    reference_dataset_cantilever = generate_reference_from_parameter_space(
        target_model, space_tool_result.parameter_space, n_samples=6, as_dataset=True
    )
    target_model_2 = create_model("BendingTestAnalytical", "ThreePoints")
    target_model_2.default_input_data["young_modulus"] = atleast_1d(
        target_young_modulus_three_points
    )
    target_model_2.cache = None
    reference_dataset_three_points = generate_reference_from_parameter_space(
        target_model_2,
        space_tool_result.parameter_space,
        n_samples=6,
        as_dataset=True,
    )

    output_name = "reaction_forces"

    step = CalibrationStep()
    step.execute(
        inputs=CalibrationStepInputs(
            reference_data={
                "Cantilever": reference_dataset_cantilever,
                "ThreePoints": reference_dataset_three_points,
            },
        ),
        settings=CalibrationStepSettings(
            name_to_models={
                "Cantilever": "BendingTestAnalytical",
                "ThreePoints": "BendingTestAnalytical",
            },
            control_outputs={
                output_name: CalibrationMetricSettings(measure="RelativeMSE")
            },
            input_names=[
                "height",
                "width",
                "imposed_dplt",
            ],
            parameter_names=["young_modulus"],
        ),
    )

    assert step.result.metric_variables == [
        MetricVariable(
            "Cantilever:reaction_forces",
            MetricVariableType.SCALAR,
        ),
        MetricVariable(
            "ThreePoints:reaction_forces",
            MetricVariableType.SCALAR,
        ),
    ]
    # We expect that the best compromise is the average value between the two
    # young modulus:
    assert step.result.posterior_parameters["young_modulus"] == pytest.approx(
        0.5 * (target_young_modulus_cantilever + target_young_modulus_three_points),
        rel=1e-2,
    )


def test_save_result(tmp_wd, calibration_on_scalars):
    """Check that a calibration result can be saved to disk."""
    calibration_step, _target_model = calibration_on_scalars
    calibration_step.save_results()


def test_plots_on_scalars(tmp_wd, calibration_on_scalars):
    """Check that a calibration step based on scalar outputs can be plotted."""
    calibration_step, _target_model = calibration_on_scalars

    calibration_step.plot_results(calibration_step.result, show=False, save=True)
    assert (
        calibration_step.working_directory
        / "simulated_versus_reference_reaction_forces_load_case_Cantilever.png"
    ).is_file()
    assert (
        calibration_step.working_directory / "opt_history_view_objective.png"
    ).is_file()
    assert (
        calibration_step.working_directory / "opt_history_view_variables.png"
    ).is_file()
    assert (
        calibration_step.working_directory / "opt_history_view_x_xstar.png"
    ).is_file()
    assert (
        calibration_step.working_directory
        / "simulated_versus_reference_reaction_forces_load_case_Cantilever_bars.html"
    ).is_file()


def test_serialization(tmp_wd, calibration_on_scalars):
    """Check that a CalibrationStepResult can be serialized to hdf5."""
    calibration_step, _ = calibration_on_scalars
    result = calibration_step.result
    result.to_hdf5("result.hdf5")
    serialized_result = CalibrationStepResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)
