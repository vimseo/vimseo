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

"""Tests for PostProcessor.POSTPROCESS_DESPITE_FAULTY_RUN / _can_postprocess(), and
for the resulting _generate_nan_outputs()/_generate_failed_output_data() behavior,
exercised end-to-end through the MockFaultyRunPost mock model rather than by
calling the private methods directly.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy import atleast_1d

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.utilities.test_utils import check_model_outputs

MODEL_NAME = "MockFaultyRunPost"
LOAD_CASE_NAME = "LC1"


def test_successful_run_postprocesses_normally(tmp_wd):
    """With a successful run, all outputs are computed normally."""
    model = check_model_outputs(
        MODEL_NAME,
        LOAD_CASE_NAME,
        input_data={"x1": atleast_1d(3.0), "run_succeeds": atleast_1d(True)},
        expected_outputs={"y1": atleast_1d(6.0), "y2": atleast_1d(9.0)},
        relative_tolerance=1e-6,
    )
    assert model.get_output_data()[MetaDataNames.error_code][0] == 0


def test_faulty_run_without_opt_in_returns_nan_outputs(tmp_wd):
    """By default (``POSTPROCESS_DESPITE_FAULTY_RUN=False``), a faulty run falls
    back to NaN outputs without attempting to postprocess, even though the job
    directory actually holds a usable result file."""
    model = create_model(MODEL_NAME, LOAD_CASE_NAME)
    model.execute({
        "x1": atleast_1d(3.0),
        "run_succeeds": atleast_1d(False),
        "result_file_written": atleast_1d(True),
    })

    output_data = model.get_output_data()
    assert output_data[MetaDataNames.error_code][0] == 1
    assert np.isnan(output_data["y1"]).all()
    assert np.isnan(output_data["y2"]).all()


def test_faulty_run_with_opt_in_recovers_available_outputs(tmp_wd):
    """With ``POSTPROCESS_DESPITE_FAULTY_RUN=True`` and a usable job directory
    (``_can_postprocess()`` returns True), postprocessing is attempted: outputs
    that can be recovered are kept, others fall back to NaN via
    ``_generate_nan_outputs(existing_data=...)``, and the run is not reported as
    an error."""
    model = create_model(MODEL_NAME, LOAD_CASE_NAME)
    model._chain.disciplines[0].POSTPROCESS_DESPITE_FAULTY_RUN = True
    model.execute({
        "x1": atleast_1d(3.0),
        "run_succeeds": atleast_1d(False),
        "result_file_written": atleast_1d(True),
    })

    output_data = model.get_output_data()
    assert output_data[MetaDataNames.error_code][0] == 0
    assert output_data["y1"][0] == pytest.approx(6.0)
    assert np.isnan(output_data["y2"]).all()


def test_faulty_run_with_opt_in_but_unusable_job_directory_returns_nan_outputs(
    tmp_wd,
):
    """With ``POSTPROCESS_DESPITE_FAULTY_RUN=True`` but no usable job directory
    (``_can_postprocess()`` returns False), postprocessing still falls back to
    NaN outputs, via ``_generate_failed_output_data()``."""
    model = create_model(MODEL_NAME, LOAD_CASE_NAME)
    model._chain.disciplines[0].POSTPROCESS_DESPITE_FAULTY_RUN = True
    model.execute({
        "x1": atleast_1d(3.0),
        "run_succeeds": atleast_1d(False),
        "result_file_written": atleast_1d(False),
    })

    output_data = model.get_output_data()
    assert output_data[MetaDataNames.error_code][0] == 1
    assert np.isnan(output_data["y1"]).all()
    assert np.isnan(output_data["y2"]).all()
