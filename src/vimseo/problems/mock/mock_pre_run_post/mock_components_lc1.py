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

X1_DEFAULT_VALUE = 0.1


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
