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

import json

import pytest
from gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings import NLOPT_COBYLA_Settings

from vimseo.analysis_nodes.calibration.calibration_metrics import (
    CalibrationMetricSettings,
)
from vimseo.analysis_nodes.calibration.calibration_step import CalibrationStep
from vimseo.analysis_nodes.calibration.calibration_step import CalibrationStepSettings
from vimseo.workflow.workflow_step import Input
from vimseo.workflow.workflow_step import Output
from vimseo.workflow.workflow_step import WorkflowStep
from vimseo.workflow.workflow_step import _deserialize_pydantic_settings


@pytest.mark.parametrize(
    "step",
    [
        WorkflowStep(
            "calibration step",
            "CalibrationStep",
            inputs=[Input("my_ref", "reference_data")],
            outputs=[Output("my_posterior", "posterior_parameters")],
            analysis_node_settings=CalibrationStepSettings(
                name_to_models={"Cantilever": "BendingTestAnalytical"},
                control_outputs={
                    "reaction_forces": CalibrationMetricSettings(metric_name="MSE")
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
    # NLOPT_COBYLA_Settings' own field set (names, order, defaults) comes from
    # stock gemseo and evolves between versions independently of vimseo/gemseo
    # -calibration; this golden value matches gemseo 6.3.3 and the official
    # gemseo-calibration 4.0.1 (field names ``output_name``/``metric_name``/
    # ``mesh_name``, ``mesh_name`` defaulting to ``""`` rather than ``None``).
    assert (
        json.dumps(step.serialized_settings)
        == '{"name": "calibration step", "analysis_node_name": "CalibrationStep", "inputs": '
        '[{"name": "my_ref", "option_key": "reference_data"}], "outputs": '
        '[{"name": "my_posterior", "attr_name": "posterior_parameters"}], '
        '"analysis_node_constructor_options": {}, "analysis_node_settings": '
        '{"name_to_models": {"Cantilever": "BendingTestAnalytical"}, '
        '"control_outputs": {"reaction_forces": '
        '{"output_name": "", "metric_name": "MSE", "mesh_name": "", "weight": null, '
        '"scaling": "NONE", "x_left_penalization_factor": 0.0, '
        '"x_right_penalization_factor": 0.0}}, "input_names": '
        '["height", "width", "imposed_dplt"], "parameter_names": '
        '["young_modulus"], "optimizer_name": "NLOPT_COBYLA", '
        '"optimizer_settings": {"__pydantic_model__": '
        '["gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings", '
        '"NLOPT_COBYLA_Settings"], "enable_progress_bar": null, "eq_tolerance": 0.01,'
        ' "ineq_tolerance": 0.0001, "log_problem": true, "max_time": 0.0, '
        '"normalize_design_space": true, "progress_bar_data_name": '
        '"ProgressBarData", "reset_iteration_counters": true, '
        '"round_ints": true, "store_jacobian": true, "use_database": true, '
        '"use_one_line_progress_bar": false, "ftol_rel": 1e-08, "ftol_abs": 1e-14, '
        '"max_iter": 1000, "scaling_threshold": null, "stop_crit_n_x": null, '
        '"xtol_rel": 1e-08, "xtol_abs": 1e-14, "stopval": -Infinity, '
        '"init_step": 0.25, "seed": 0}}}'
    )


def test_serialized_settings_to_step():
    serialized_settings = {
        "name": "a step",
        "analysis_node_name": "CalibrationStep",
        "inputs": [{"name": "i1", "option_key": "starting_point"}],
        "outputs": [{"name": "o1", "attr_name": "posterior_parameters"}],
        "analysis_node_settings": {
            "name_to_models": {"Cantilever": "BendingTestAnalytical"},
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
    assert isinstance(step.analysis_node, CalibrationStep)
    assert isinstance(step.inputs[0], Input)
    assert isinstance(step.outputs[0], Output)
    analysis_node_settings = step.analysis_node_settings
    assert analysis_node_settings.name_to_models == {
        "Cantilever": "BendingTestAnalytical"
    }
    assert isinstance(analysis_node_settings.optimizer_settings, NLOPT_COBYLA_Settings)
    assert analysis_node_settings.optimizer_settings.model_dump()["init_step"] == 0.5  # ruff: ignore[float-equality-comparison]


_METRIC_SETTINGS = {
    "__pydantic_model__": (
        "vimseo.analysis_nodes.calibration.calibration_metrics",
        "CalibrationMetricSettings",
    ),
    "metric_name": "MSE",
}


def test_serialized_settings_with_a_mapping_of_pydantic_models_to_step():
    """A pydantic model which is a value of a mapping setting is deserialized."""
    step = WorkflowStep.from_serialized_settings(
        name="a step",
        analysis_node_name="CalibrationStep",
        analysis_node_settings={
            "name_to_models": {"Cantilever": "BendingTestAnalytical"},
            "control_outputs": {"reaction_forces": dict(_METRIC_SETTINGS)},
        },
    )
    metric_settings = step.analysis_node_settings.control_outputs["reaction_forces"]
    assert isinstance(metric_settings, CalibrationMetricSettings)
    assert metric_settings.metric_name == "MSE"


def test_deserialize_pydantic_models_nested_in_mappings():
    """The pydantic models are deserialized up to two levels of mappings."""
    settings = _deserialize_pydantic_settings({
        "a": {"b": {"c": dict(_METRIC_SETTINGS)}},
    })
    assert isinstance(settings["a"]["b"]["c"], CalibrationMetricSettings)
