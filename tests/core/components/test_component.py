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

import vimseo.problems.mock.mock_component.mock_component as mc
from vimseo.core.components.component_factory import ComponentFactory

JOB_NAME = "DummyJobDir"


def test_grammar_from_parent_class_inherit(tmp_wd):
    """Test case where the grammars are inherited from parent classes."""
    factory = ComponentFactory()
    mcc1 = factory.create("MockChildComponent1")
    assert list(mcc1.io.input_grammar.keys()) == ["x1", "x2", "x3"]
    assert list(mcc1.io.output_grammar.keys()) == ["y1", "y2", "y3"]
    assert mcc1.default_input_data == {"x1": 0.0, "x2": 0.0, "x3": 0.0}


def test_required_input(tmp_wd):
    """Test case where the required input are checked."""
    mpc3 = mc.MockComponent()
    assert mpc3.input_grammar.required_names == {"x1", "x2", "x3"}
