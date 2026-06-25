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


class MockModel(PreRunPostModel):
    """Mock Class to test the creation of a model."""

    SUMMARY = (
        " A toy model implementing an unphysical analytical law;"
        " used for testing purpose"
    )
    PRE_PROC_FAMILY = "MockPre"  # x2 = x1 + 2
    RUN_FAMILY = "MockRun"  # y0 = x2 * 2
    POST_PROC_FAMILY = "MockPost"  # y1 = y0 + 1
