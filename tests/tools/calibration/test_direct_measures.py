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

import pytest
from numpy import atleast_1d
from numpy import mean

from vimseo.api import create_model
from vimseo.direct_measures.curve_measure import DirectMeasureOnCurveSettings
from vimseo.direct_measures.curve_measure import DummyModulus
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.tools.calibration.direct_measure_calibration_step import DirectMeasures
from vimseo.tools.calibration.direct_measure_calibration_step import (
    DirectMeasuresInputs,
)
from vimseo.tools.calibration.direct_measure_calibration_step import (
    DirectMeasuresSettings,
)
from vimseo.tools.calibration.input_data import CALIBRATION_INPUT_DATA
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_parameter_space,
)


def test_calibration_on_stress_strain_curve(tmp_wd):
    space_tool_result = SpaceToolFileIO().read(
        CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
    )
    target_model = create_model("BendingTestAnalytical", "Cantilever")
    target_model.EXTRA_INPUT_GRAMMAR_CHECK = True
    target_model.default_input_data["young_modulus"] = atleast_1d(
        DummyModulus.IMPOSED_MODULUS
    )
    target_model.cache = None
    reference_dataset_cantilever = generate_reference_from_parameter_space(
        target_model,
        space_tool_result.parameter_space,
        n_samples=6,
        as_dataset=True,
    )

    calibration = DirectMeasures()
    calibration.execute(
        inputs=DirectMeasuresInputs(reference_data=reference_dataset_cantilever),
        settings=DirectMeasuresSettings(
            direct_measure_settings={
                "E1": DirectMeasureOnCurveSettings(
                    x_name="dplt_grid",
                    y_name="dplt",
                    measure_name="DummyModulus",
                )
            }
        ),
    )
    assert list(calibration.result.direct_measures.keys()) == ["E1"]
    assert mean(calibration.result.direct_measures["E1"]) == pytest.approx(
        DummyModulus.IMPOSED_MODULUS
    )
    assert calibration.result.mean_direct_measures["E1"] == pytest.approx(
        DummyModulus.IMPOSED_MODULUS
    )
