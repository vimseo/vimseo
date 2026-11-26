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

import pytest
from numpy import array

import vimseo.problems.mock.mock_component.mock_component as mc
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.model_metadata import MetaDataNames

JOB_NAME = "DummyJobDir"


def test_grammar_from_parent_class_inherit(tmp_wd):
    """Test case where the grammars are inherited from parent classes."""
    factory = ComponentFactory()
    mcc1 = factory.create("MockChildComponent1")
    # Every component declares an optional error code, as input and output.
    assert list(mcc1.io.input_grammar.keys()) == ["x1", "x2", "x3", "error_code"]
    assert list(mcc1.io.output_grammar.keys()) == ["y1", "y2", "y3", "error_code"]
    assert mcc1.default_input_data == {"x1": 0.0, "x2": 0.0, "x3": 0.0}


def test_error_code_declared_but_not_required(tmp_wd):
    """A component declares the error code as an optional output, so that an error
    code it returns reaches the model metadata, without forcing it to return one.

    It also declares it as an optional input, to read the upstream error code.
    """
    component = ComponentFactory().create("MockChildComponent1")
    for grammar in (component.input_grammar, component.output_grammar):
        assert MetaDataNames.error_code.name in grammar
        assert MetaDataNames.error_code.name not in grammar.required_names

    output_data = component.execute()

    assert MetaDataNames.error_code.name not in output_data


def test_error_code_declared_in_grammar_file_is_kept(tmp_wd, tmp_path):
    """An error code already declared by the grammar file of a component is not
    overridden, so that it stays required."""
    (tmp_path / "ComponentWithErrorCode_input.json").write_text(
        json.dumps({"type": "object", "properties": {}})
    )
    (tmp_path / "ComponentWithErrorCode_output.json").write_text(
        json.dumps({
            "type": "object",
            "required": [MetaDataNames.error_code.name],
            "properties": {
                MetaDataNames.error_code.name: {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            },
        })
    )

    class ComponentWithErrorCode(BaseComponent):
        GRAMMAR_DIRECTORY = tmp_path

        def _run(self, input_data):
            return {}

    component = ComponentWithErrorCode()
    assert MetaDataNames.error_code.name in component.output_grammar.required_names


def test_error_code_passed_on_when_not_returned(tmp_wd):
    """A component that does not return an error code passes the upstream one on."""
    component = ComponentFactory().create("MockChildComponent1")

    component.execute({MetaDataNames.error_code.name: array([1])})

    assert component.get_output_data()[MetaDataNames.error_code.name] == array([1])


def test_error_code_returned_overrides_upstream_one(tmp_wd):
    """The error code returned by a component overrides the upstream one, e.g. when
    it could recover from an upstream error."""

    class RecoveringComponent(BaseComponent):
        auto_detect_grammar_files = False

        def _run(self, input_data):
            return {MetaDataNames.error_code.name: array([0])}

    component = RecoveringComponent()

    component.execute({MetaDataNames.error_code.name: array([1])})

    assert component.get_output_data()[MetaDataNames.error_code.name] == array([0])


@pytest.mark.parametrize(
    ("input_data", "expected"),
    [
        ({}, 0),
        ({MetaDataNames.error_code.name: array([0])}, 0),
        ({MetaDataNames.error_code.name: array([1])}, 1),
        ({MetaDataNames.error_code.name: array([-1])}, -1),
    ],
)
def test_get_upstream_error_code(input_data, expected):
    """The upstream error code is 0 when no upstream component reported one."""
    assert BaseComponent._get_upstream_error_code(input_data) == expected


def test_error_code_name_cannot_be_customized():
    """A component cannot rename its error code, otherwise the model would miss it."""
    with pytest.raises(AttributeError, match="_ERROR_CODE_NAME"):

        class ComponentWithCustomErrorCodeName(BaseComponent):
            _ERROR_CODE_NAME = "error_foo"


def test_required_input(tmp_wd):
    """Test case where the required input are checked."""
    mpc3 = mc.MockComponent()
    assert mpc3.input_grammar.required_names == {"x1", "x2", "x3"}


class _SimpleGrammarComponent(BaseComponent):
    """A component using a SimpleGrammar, which cannot hold a material grammar."""

    auto_detect_grammar_files = False
    default_grammar_type = BaseComponent.GrammarType.SIMPLE

    def _run(self, input_data):
        return {}


def test_material_grammar_requires_a_json_grammar(tmp_wd):
    """Check that a material grammar given to a component with a non-JSON grammar
    raises an explicit error (#100)."""
    from vimseo.material_lib import MATERIAL_LIB_DIR

    with pytest.raises(TypeError, match=r"can only be loaded into a JSONGrammar"):
        _SimpleGrammarComponent(
            material_grammar_file=MATERIAL_LIB_DIR / "Mock_grammar.json"
        )


def test_simple_grammar_without_material(tmp_wd):
    """Check that a component with a non-JSON grammar and no material is accepted."""
    _SimpleGrammarComponent()
