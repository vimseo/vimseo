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

import json

import pytest
from gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings import NLOPT_COBYLA_Settings
from gemseo_calibration.calibrator import CalibrationMetricSettings

from vimseo.tools.calibration.calibration_step import CalibrationStep
from vimseo.tools.calibration.calibration_step import CalibrationStepSettings
from vimseo.workflow.workflow_step import Input
from vimseo.workflow.workflow_step import Output
from vimseo.workflow.workflow_step import WorkflowStep


@pytest.mark.parametrize(
    "step",
    [
        WorkflowStep(
            "calibration step",
            "CalibrationStep",
            inputs=[Input("my_ref", "reference_data")],
            outputs=[Output("my_posterior", "posterior_parameters")],
            tool_settings=CalibrationStepSettings(
                model_name={"Cantilever": "BendingTestAnalytical"},
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
        ),
    ],
)
def test_to_serializable_settings(step):
    assert (
        json.dumps(step.serialized_settings)
        == '{"name": "calibration step", "tool_name": "CalibrationStep", "inputs": '
        '[{"name": "my_ref", "option_key": "reference_data"}], "outputs": '
        '[{"name": "my_posterior", "attr_name": "posterior_parameters"}], '
        '"tool_constructor_options": {}, "tool_settings": '
        '{"model_name": {"Cantilever": "BendingTestAnalytical"}, '
        '"control_outputs": {"reaction_forces": '
        '{"output": "", "measure": "MSE", "mesh": null, "weight": null, '
        '"scaling": "NONE", "x_left_penalization_factor": 0.0, '
        '"x_right_penalization_factor": 0.0}}, "input_names": '
        '["height", "width", "imposed_dplt"], "parameter_names": '
        '["young_modulus"], "optimizer_name": "NLOPT_COBYLA", '
        '"optimizer_settings": {"__pydantic_model__": '
        '["gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings", '
        '"NLOPT_COBYLA_Settings"], "enable_progress_bar": null, "eq_tolerance": 0.01,'
        ' "ineq_tolerance": 0.0001, "log_problem": true, "max_time": 0.0, '
        '"normalize_design_space": true, "reset_iteration_counters": true, '
        '"round_ints": true, "use_database": true, "use_one_line_progress_bar": '
        'false, "store_jacobian": true, "ftol_rel": 1e-08, "ftol_abs": 1e-14, '
        '"max_iter": 1000, "scaling_threshold": null, "stop_crit_n_x": null, '
        '"xtol_rel": 1e-08, "xtol_abs": 1e-14, "stopval": -Infinity, '
        '"init_step": 0.25}}}'
    )


def test_serialized_settings_to_step():
    serialized_settings = {
        "name": "a step",
        "tool_name": "CalibrationStep",
        "inputs": [{"name": "i1", "option_key": "starting_point"}],
        "outputs": [{"name": "o1", "attr_name": "posterior_parameters"}],
        "tool_settings": {
            "model_name": {"Cantilever": "BendingTestAnalytical"},
            "optimizer_settings": {
                "__pydantic_model__": (
                    "gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings",
                    "NLOPT_COBYLA_Settings",
                ),
                "init_step": 0.5,
            },
        },
    }
    step = WorkflowStep.from_serialized_settings(**serialized_settings)
    assert isinstance(step.tool, CalibrationStep)
    assert isinstance(step.inputs[0], Input)
    assert isinstance(step.outputs[0], Output)
    tool_settings = step.tool_settings
    assert tool_settings.model_name == {"Cantilever": "BendingTestAnalytical"}
    assert isinstance(tool_settings.optimizer_settings, NLOPT_COBYLA_Settings)
    assert tool_settings.optimizer_settings.model_dump()["init_step"] == 0.5  # noqa: RUF069
