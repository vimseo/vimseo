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

import time

from numpy import array
from numpy import atleast_1d

from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.core.components.post.post_processor import PostProcessor
from vimseo.problems.mock import X1_DEFAULT_VALUE


class MockSleepPre(ExternalSoftwareComponent):
    """Mock Class for pre-processing that sleeps for a configurable duration."""

    USE_JOB_DIRECTORY = False


class MockSleepPre_LC1(MockSleepPre):
    """Mock Class for pre-processing with a load case, sleeping ``pre_duration``
    seconds.

    Also carries ``run_duration`` and ``post_duration`` as inputs, so that they flow
    through to the run and post components of :class:`.MockModelSleep`.
    """

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.default_input_data.update({
            "x1": atleast_1d(X1_DEFAULT_VALUE),
            "pre_duration": atleast_1d(30.0),
            "run_duration": atleast_1d(30.0),
            "post_duration": atleast_1d(30.0),
        })

    def _run(self, input_data):
        time.sleep(float(input_data["pre_duration"][0]))
        x2 = input_data["x1"] + 2
        return {"x2": x2}


class MockSleepRun(ExternalSoftwareComponent):
    """Mock Class for run, sleeping ``run_duration`` seconds.

    Passes ``post_duration`` through unchanged, since the post component needs it as
    an input.
    """

    def _run(self, input_data):
        time.sleep(float(input_data["run_duration"][0]))
        y0 = input_data["x2"] * 2
        return {"y0": y0, "post_duration": input_data["post_duration"]}


class MockSleepPost(PostProcessor):
    """Mock Class for post-processing that sleeps for a configurable duration."""


class MockSleepPost_LC1(MockSleepPost):
    """Mock Class for post-processing with a loadcase, sleeping ``post_duration``
    seconds."""

    def _run(self, input_data):
        time.sleep(float(input_data["post_duration"][0]))
        y1 = input_data["y0"] + 1
        return {"y1": y1, "error_code": array([0])}
