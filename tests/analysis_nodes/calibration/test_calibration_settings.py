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

from gemseo.algos.opt.multi_start.settings.multi_start_settings import (
    MultiStart_Settings,
)
from numpy import atleast_1d

from vimseo.analysis_nodes.calibration.calibration_metrics import (
    CalibrationMetricSettings,
)
from vimseo.analysis_nodes.calibration.calibration_step import CalibrationStep
from vimseo.analysis_nodes.calibration.calibration_step import CalibrationStepInputs
from vimseo.analysis_nodes.calibration.calibration_step import CalibrationStepSettings
from vimseo.analysis_nodes.calibration.input_data import CALIBRATION_INPUT_DATA
from vimseo.api import create_model
from vimseo.io.space_io import SpaceAnalysisNodeFileIO
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_parameter_space,
)

TARGET_YOUNG_MODULUS = 2.2e5


def test_specific_settings(tmp_wd):
    """Check that prescribing when passing a specific optimizer and its settings, all
    settings are taken into account.

    Subclass MultiStart_Settings`` extends ``BaseOptimizerSettings``,
    thus the ``serialize_as_any`` option from Pydantic is mandatory,
    which is defined in [vimseo][analysis_nodes][base_settings][BaseSettings].
    """
    space_analysis_node_result = SpaceAnalysisNodeFileIO().read(
        CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
    )
    target_model = create_model("BendingTestAnalytical", "Cantilever")
    target_model.default_input_data["young_modulus"] = atleast_1d(TARGET_YOUNG_MODULUS)
    target_model.cache = None
    reference_dataset_cantilever = generate_reference_from_parameter_space(
        target_model,
        space_analysis_node_result.parameter_space,
        n_samples=6,
        as_dataset=True,
    )

    sub_optimizer_name = "NLOPT_COBYLA"
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
                "reaction_forces": CalibrationMetricSettings(metric_name="MSE")
            },
            parameter_names=["young_modulus"],
            optimizer_name="MultiStart",
            optimizer_settings=MultiStart_Settings(
                opt_algo_name=sub_optimizer_name, max_iter=10
            ),
        ),
    )
    assert step.options["optimizer_settings"]["opt_algo_name"] == sub_optimizer_name
