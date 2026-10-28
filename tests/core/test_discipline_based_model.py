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

import json
import re

import pytest
from gemseo.core.discipline import Discipline
from gemseo.core.grammars.errors import InvalidDataError
from gemseo.core.grammars.json_grammar import JSONGrammar
from numpy import atleast_1d

from vimseo.api import create_model
from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.material.material import Material
from vimseo.material_lib import MATERIAL_LIB_DIR


def test_discipline_based_model(tmp_wd):
    """Check that a model created from a GEMSEO discipline executes correctly."""
    model = create_model("MockCurves", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    output_data = model.execute()
    assert output_data["x"][0] == 1.0  # ruff: ignore[float-equality-comparison]
    assert output_data["x_1"][0] == 1.0  # ruff: ignore[float-equality-comparison]
    for name in ["x_history", "y_history"]:
        assert (
            len(output_data[name])
            == model._chain.disciplines[0]._discipline.CURVE_NB_POINTS
        )


def test_discipline_isolation(tmp_wd):
    """Check that all model instances are isolated (no interference through class
    attribute ``_DISCIPLINE``."""

    model = create_model("MockCurves", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    model_bis = create_model("MockCurves", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model_bis.default_input_data.update({"x": atleast_1d(2.0)})

    assert model.default_input_data["x"][0] == 1.0  # ruff: ignore[float-equality-comparison]


class _CountingDiscipline(Discipline):
    """A discipline counting its executions, with the default GEMSEO cache."""

    def __init__(self):
        super().__init__()
        self.input_grammar.update_from_data({"x": atleast_1d(0.0)})
        self.output_grammar.update_from_data({"y": atleast_1d(0.0)})
        self.default_input_data = {"x": atleast_1d(1.0)}
        self.n_calls = 0

    def _run(self, input_data):
        self.n_calls += 1
        return {"y": 2 * input_data["x"]}


class _CountingModel(BaseDisciplineModel):
    _DISCIPLINE = _CountingDiscipline()
    _EXPECTED_LOAD_CASE = "Dummy"


def test_wrapped_discipline_cache_is_disabled(tmp_wd):
    """The model manages the cache: once the model cache is disabled, the wrapped
    discipline is executed at each model execution."""
    model = _CountingModel()
    discipline = model.run._discipline
    assert discipline.cache is None

    model.cache = None
    model.execute()
    model.execute()
    assert discipline.n_calls == 2


class _StiffnessDiscipline(Discipline):
    """A discipline whose input ``E1`` is the property of the ``Mock`` material."""

    def __init__(self):
        super().__init__()
        self.input_grammar.update_from_data({
            "E1": atleast_1d(0.0),
            "area": atleast_1d(0.0),
        })
        self.output_grammar.update_from_data({"stiffness": atleast_1d(0.0)})
        self.default_input_data = {"E1": atleast_1d(1.0), "area": atleast_1d(2.0)}

    def _run(self, input_data):
        return {"stiffness": input_data["E1"] * input_data["area"]}


class _ModelWithMaterial(BaseDisciplineModel):
    MATERIAL_FILE = MATERIAL_LIB_DIR / "Mock.json"
    _DISCIPLINE = _StiffnessDiscipline()
    _EXPECTED_LOAD_CASE = "Dummy"


def test_material_values_are_default_inputs(tmp_wd):
    """The values of the material declared by ``MATERIAL_FILE`` are default inputs,
    while the other default inputs and the class discipline are left unchanged."""
    model = _ModelWithMaterial()

    assert model.material_variable_names == ["E1"]
    assert model.default_input_data["E1"][0] == 150000.0  # ruff: ignore[float-equality-comparison]
    assert model.default_input_data["area"][0] == 2.0  # ruff: ignore[float-equality-comparison]
    assert model.execute()["stiffness"][0] == 300000.0  # ruff: ignore[float-equality-comparison]
    assert _ModelWithMaterial._DISCIPLINE.default_input_data["E1"][0] == 1.0  # ruff: ignore[float-equality-comparison]


def test_material_argument_overrides_material_file(tmp_wd):
    """A material passed to the constructor overrides ``MATERIAL_FILE``."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Mock.json")
    material.update_from_dict({"E1": 120000.0})
    model = _ModelWithMaterial(material=material)

    assert model.material is material
    assert model.default_input_data["E1"][0] == 120000.0  # ruff: ignore[float-equality-comparison]


def test_material_property_not_an_input(tmp_wd):
    """A material property must be an input of the discipline."""
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The properties ['E1'] of the material MockDefaultMaterial are not inputs "
            "of the discipline _CountingDiscipline."
        ),
    ):
        _CountingModel(material=MATERIAL_LIB_DIR / "Mock.json")


def _write_input_grammar(file_path, properties):
    file_path.write_text(json.dumps({"type": "object", "properties": properties}))
    return file_path


def test_input_grammar_file(tmp_wd):
    """The input grammar file bounds the inputs, keeping the default values, the
    required names and the cache."""
    file_path = _write_input_grammar(
        tmp_wd / "input.json",
        {
            "area": {
                "type": "array",
                "items": {"type": "number", "minimum": 1.0, "maximum": 3.0},
            }
        },
    )

    class _BoundedModel(_ModelWithMaterial):
        _INPUT_GRAMMAR_FILE = file_path

    model = _BoundedModel()

    assert isinstance(model.input_grammar, JSONGrammar)
    assert model.lower_bounds == {"area": 1.0}
    assert model.upper_bounds == {"area": 3.0}
    assert set(model.input_grammar.required_names) == {"E1", "area"}
    assert model.default_input_data["E1"][0] == 150000.0  # ruff: ignore[float-equality-comparison]
    assert model.execute()["stiffness"][0] == 300000.0  # ruff: ignore[float-equality-comparison]
    model.execute()
    assert len(model.cache) == 1
    with pytest.raises(
        InvalidDataError, match=r"must be smaller than or equal to 3\.0"
    ):
        model.execute({"area": atleast_1d(4.0)})


def test_input_grammar_file_only_restricts(tmp_wd):
    """The input grammar file cannot change the type of an input."""
    file_path = _write_input_grammar(
        tmp_wd / "input.json", {"area": {"type": "number"}}
    )

    class _BadModel(_ModelWithMaterial):
        _INPUT_GRAMMAR_FILE = file_path

    with pytest.raises(ValueError, match="shall only restrict"):
        _BadModel()
