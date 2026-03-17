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

from vimseo.problems.mock.mock_pre_run_post.mock_components_lc1 import MockPost
from vimseo.problems.mock.mock_pre_run_post.mock_components_lc1 import MockPre

X1_DEFAULT_VALUE = 0.1


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


class MockPost_LC2(MockPost):
    """Mock Class for post-processing with a load case having two output scalar
    variables."""

    ERROR_VALUE = 0

    def _run(self, input_data):
        y0 = input_data["y0"]
        y1 = y0 + 1
        y1_2 = y1 + 1
        return {"y1": y1, "y1_2": y1_2, "error_code": array([self.ERROR_VALUE])}
