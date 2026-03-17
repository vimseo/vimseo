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

from numpy import array
from numpy import atleast_1d

from vimseo.core.components.post.post_processor import PostProcessor
from vimseo.core.components.pre.pre_processor import PreProcessor
from vimseo.core.components.run.run_processor import RunProcessor
from vimseo.core.pre_run_post_model import PreRunPostModel
from vimseo.material_lib import MATERIAL_LIB_DIR

X1_DEFAULT_VALUE = 0.1


def mock_model_lc1_overall_function(x1):
    """The overall input to output function representing the MockModel load case LC1."""
    return (x1 + 2) * 2 + 1


def mock_model_lc2_overall_function(x1, x1_2):
    """The overall input to output function representing the MockModel load case LC2."""
    y1 = (x1 + x1_2 + 2) * 2 + 1
    return y1, y1 + 1


class MockModel(PreRunPostModel):
    """Mock Class to test the creation of a model."""

    SUMMARY = (
        " A toy model implementing an unphysical analytical law;"
        " used for testing purpose"
    )
    PRE_PROC_FAMILY = "MockPre"  # x2 = x1 + 2
    RUN_FAMILY = "MockRun"  # y0 = x2 * 2
    POST_PROC_FAMILY = "MockPost"  # y1 = y0 + 1


class MockModelWithMaterial(MockModel):
    """Mock model to test loading of a material file."""

    SUMMARY = "A toy model loading a material"
    _MATERIAL_GRAMMAR_FILE = MATERIAL_LIB_DIR / "Mock_grammar.json"
    MATERIAL_FILE = MATERIAL_LIB_DIR / "Mock.json"


class MockPre(PreProcessor):
    """Mock Class for pre-processing."""

    USE_JOB_DIRECTORY = False


class MockPre_LC1(MockPre):
    """Mock Class for pre-processing with a load case."""

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.default_input_data.update({
            "x1": atleast_1d(X1_DEFAULT_VALUE),
            "x1_maximum_only": atleast_1d(X1_DEFAULT_VALUE),
            "x1_minimum_only": atleast_1d(X1_DEFAULT_VALUE),
            "x1_no_bounds": atleast_1d(X1_DEFAULT_VALUE),
        })

    def _run(self, input_data):
        x1 = input_data["x1"]
        x2 = x1 + 2
        return {"x2": x2}


class MockPre_LC2(MockPre):
    """Mock Class for pre-processing with a load case having two inputs variables."""

    def __init__(self, **options):
        super().__init__(**options)
        self.default_input_data.update({
            "x1": atleast_1d(X1_DEFAULT_VALUE),
            "x1_2": atleast_1d(0.0),
        })

    def _run(self, input_data):
        x1 = input_data["x1"]
        x1_2 = input_data["x1_2"]
        x2 = x1 + x1_2 + 2
        return {"x2": x2}


class MockRun(RunProcessor):
    """Mock Class for run."""

    def _run(self, input_data):
        x2 = input_data["x2"]
        y0 = x2 * 2
        return {"y0": y0}


class MockPost(PostProcessor):
    """Mock Class for post-processing."""


class MockPost_LC1(MockPost):
    """Mock Class for post-processing with a loadcase."""

    def _run(self, input_data):
        y0 = input_data["y0"]
        y1 = y0 + 1
        return {"y1": y1, "error_code": array([0])}


class MockPost_LC2(MockPost):
    """Mock Class for post-processing with a load case having two output scalar
    variables."""

    ERROR_VALUE = 0

    def _run(self, input_data):
        y0 = input_data["y0"]
        y1 = y0 + 1
        y1_2 = y1 + 1
        return {"y1": y1, "y1_2": y1_2, "error_code": array([self.ERROR_VALUE])}
