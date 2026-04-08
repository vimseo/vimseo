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

from vimseo.api import get_available_load_cases
from vimseo.api import get_available_models


def test_available_load_cases(tmp_wd):
    """Check the load cases available for a model."""
    assert get_available_load_cases("MockModel") == ["LC1", "LC2"]
    assert get_available_load_cases("BendingTestAnalytical") == [
        "Cantilever",
        "ThreePoints",
    ]


def test_available_models(tmp_wd):
    """Check that the models associated with a given load case are correctly found."""
    assert set(get_available_models("LC1")) == {
        "MockModel",
        "MockModelFields",
        "MockModelPersistent",
        "MockModelWithMaterial",
        "MockExternalSoftware",
    }
