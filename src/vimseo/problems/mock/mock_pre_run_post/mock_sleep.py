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

from vimseo.core.pre_run_post_model import PreRunPostModel


class MockModelSleep(PreRunPostModel):
    """Mock model with independently configurable pre/run/post durations.

    Used for manual testing of the VTT/VIMSEO daemon bridge against a long-running
    model: each of the pre-processing, run, and post-processing phases sleeps for a
    configurable duration (``pre_duration``, ``run_duration``, ``post_duration``, in
    seconds), defaulting to 30 seconds each.
    """

    SUMMARY = (
        "A toy model with configurable pre/run/post sleep durations; "
        "used for manual daemon-bridge testing"
    )
    PRE_PROC_FAMILY = "MockSleepPre"  # x2 = x1 + 2
    RUN_FAMILY = "MockSleepRun"  # y0 = x2 * 2
    POST_PROC_FAMILY = "MockSleepPost"  # y1 = y0 + 1
