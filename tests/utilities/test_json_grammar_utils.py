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
from gemseo.core.grammars.json_grammar import JSONGrammar
from gemseo.core.grammars.simple_grammar import SimpleGrammar
from numpy import array

from vimseo.material.material import Material
from vimseo.material.material_property import MaterialProperty
from vimseo.material.material_relation import MaterialRelation
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder
from vimseo.utilities.json_grammar_utils import check_grammar_restriction
from vimseo.utilities.json_grammar_utils import check_material_bounds
from vimseo.utilities.json_grammar_utils import to_json_grammar


def test_enhanced_json_encoder_serializes_grammar_defaults():
    """A grammar's ``Defaults`` mapping is serialized as a plain dict."""
    grammar = JSONGrammar("test")
    grammar.update_from_data({"x": 1.0})
    grammar.defaults["x"] = 1.0

    text = json.dumps(grammar.defaults, cls=EnhancedJSONEncoder)

    assert json.loads(text) == {"x": 1.0}


def test_to_json_grammar_from_simple_grammar():
    """A simple grammar is converted from the types of its variables."""
    grammar = SimpleGrammar("g")
    grammar.update_from_data({"x": array([1.0])})

    json_grammar = to_json_grammar(grammar, "h")

    assert json_grammar.name == "h"
    assert json_grammar.schema["properties"] == {
        "x": {"type": "array", "items": {"type": "number"}}
    }


def test_to_json_grammar_copies_a_json_grammar():
    """A JSON grammar is copied with its bounds, under its own name by default."""
    grammar = JSONGrammar("g")
    grammar.update_from_schema({
        "type": "object",
        "properties": {
            "x": {"type": "array", "items": {"type": "number", "minimum": 0.0}}
        },
    })

    json_grammar = to_json_grammar(grammar)

    assert json_grammar is not grammar
    assert json_grammar.name == "g"
    assert json_grammar.schema["properties"]["x"]["items"]["minimum"] == 0.0  # ruff: ignore[float-equality-comparison]


def _write_properties(path, properties):
    path.write_text(json.dumps({"type": "object", "properties": properties}))
    return path


@pytest.fixture
def reference():
    """A reference grammar, ``x`` being bounded in [0, 1] and ``y`` not."""
    grammar = JSONGrammar("ref")
    grammar.update_from_schema({
        "type": "object",
        "properties": {
            "x": {
                "type": "array",
                "items": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "y": {"type": "array", "items": {"type": "number"}},
        },
    })
    return grammar


def test_check_grammar_restriction(tmp_path, reference):
    """A file restricting the bounds of the reference grammar is accepted."""
    properties = {
        "x": {"type": "array", "items": {"type": "number", "minimum": 0.5}},
        "y": {"type": "array", "items": {"type": "number", "maximum": 2.0}},
    }
    properties["x"]["items"]["maximum"] = 1.0

    check_grammar_restriction(
        reference, _write_properties(tmp_path / "g.json", properties)
    )


_X = {"type": "array", "items": {"type": "number", "minimum": 0.0, "maximum": 1.0}}
_Y = {"type": "array", "items": {"type": "number"}}


@pytest.mark.parametrize(
    ("properties", "error"),
    [
        (
            {"x": _X, "y": _Y, "z": _Y},
            "unknown variables ['z']",
        ),
        ({"x": _X}, "missing variables ['y']"),
        (
            {"x": _X, "y": {"type": "number"}},
            "y: type ('number', None) instead of ('array', 'number')",
        ),
        (
            {
                "x": {"type": "array", "items": {"type": "number", "minimum": -1.0}},
                "y": _Y,
            },
            "x: minimum -1.0 looser than 0.0; x: maximum None looser than 1.0",
        ),
    ],
)
def test_check_grammar_restriction_error(tmp_path, reference, properties, error):
    """A file declaring an unknown variable, missing a variable, changing a type or
    loosening a bound is rejected."""
    file_path = _write_properties(tmp_path / "g.json", properties)
    with pytest.raises(
        ValueError,
        match=re.escape(
            f"The JSON grammar {file_path} shall declare all the variables of the "
            f"grammar ref and only restrict them: {error}."
        ),
    ):
        check_grammar_restriction(reference, file_path)


def _material(**bounds):
    return Material(
        name="mat",
        material_relations=[
            MaterialRelation(
                name="rel",
                properties=[
                    MaterialProperty(name="x", value=0.5, **bounds),
                    MaterialProperty(name="y", value=10.0),
                ],
            )
        ],
    )


def test_check_material_bounds(reference):
    """A material within the bounds of the grammar is accepted, its properties without
    grammar bounds being unchecked."""
    check_material_bounds(_material(lower_bound=0.2, upper_bound=1.0), reference)


def test_check_material_bounds_error(reference):
    """A material with looser bounds than the grammar is rejected."""
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The material mat shall be within the bounds of the grammar ref: "
            "x: lower bound -1.0 looser than 0.0; x: upper bound 2.0 looser than 1.0."
        ),
    ):
        check_material_bounds(_material(lower_bound=-1.0, upper_bound=2.0), reference)
