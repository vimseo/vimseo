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

from numbers import Number

import pytest

from vimseo.api import create_model
from vimseo.core.inputs_handler import InputDataHandler


@pytest.fixture
def input_data_handler():
    """A handler of model default inputs."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    return model, InputDataHandler(model)


def test_get_data(tmp_wd, input_data_handler):
    """Check that the retrieved data have expected names and values, for each kind of
    variable."""
    model, handler = input_data_handler

    all_input_data = {}
    all_input_data.update(handler.get_numerical_data())
    all_input_data.update(handler.get_material_data())
    all_input_data.update(handler.get_geometrical_data())
    all_input_data.update(handler.get_boundary_condition_data())

    for name, value in all_input_data.items():
        assert isinstance(value, (Number, str))
        assert value == pytest.approx(model.default_input_data[name])


def test_set_data(tmp_wd, input_data_handler):
    """Check that model default inputs are correctly modified after calling set()
    methods."""
    model, handler = input_data_handler

    assert model.default_input_data["length"][0] == pytest.approx(600.0)
    handler.set_data({"length": 800.0})
    assert model.default_input_data["length"][0] == pytest.approx(800.0)


def test_no_boundary_nor_numerical_properties(tmp_wd):
    """Check degenerated case where the model has no boundary condition nor numerical
    properties."""
    model = create_model("MockModel", "LC2")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    handler = InputDataHandler(model)
    assert handler.get_numerical_data() == {}
    assert handler.get_boundary_condition_data() == {}
    assert handler.get_geometrical_data() == {
        name: value[0] for name, value in model.default_input_data.items()
    }
    assert handler.get_material_data() == {}
