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

from vimseo.material_lib import MATERIAL_LIB_DIR
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel


class MockModelWithMaterial(MockModel):
    """Mock model to test loading of a material file."""

    SUMMARY = "A toy model loading a material"
    _MATERIAL_GRAMMAR_FILE = MATERIAL_LIB_DIR / "Mock_grammar.json"
    MATERIAL_FILE = MATERIAL_LIB_DIR / "Mock.json"
