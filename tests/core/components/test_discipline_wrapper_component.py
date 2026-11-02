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
from gemseo.core.grammars.errors import InvalidDataError
from gemseo.core.grammars.json_grammar import JSONGrammar
from gemseo.disciplines.analytic import AnalyticDiscipline
from numpy import array

from vimseo.api import create_model
from vimseo.core.components.discipline_wrapper_component import (
    DisciplineWrapperComponent,
)
from vimseo.core.load_case import LoadCase


def test_job_executor_is_none_for_a_plain_discipline():
    """A wrapped plain GEMSEO discipline has no job executor of its own."""
    discipline = AnalyticDiscipline({"y": "x+1"})
    component = DisciplineWrapperComponent(LoadCase(name="LC1"), discipline)

    assert component.job_executor is None


def test_job_executor_forwards_the_wrapped_models_one(tmp_wd):
    """Wrapping an integrated model forwards its own job executor."""
    inner_model = create_model("MockModel", "LC1")
    component = DisciplineWrapperComponent(LoadCase(name="LC1"), inner_model)

    assert component.job_executor is inner_model.job_executor


def test_input_grammar_is_shared_without_file(tmp_wd):
    """Without input grammar file, the component shares the discipline grammar."""
    discipline = AnalyticDiscipline({"y": "x+1"})
    component = DisciplineWrapperComponent(LoadCase(name="LC1"), discipline)

    assert component.input_grammar is discipline.input_grammar


def test_input_grammar_file(tmp_wd):
    """With an input grammar file, the component has its own JSON grammar, restricted
    by the file and keeping the default values of the discipline, whose grammar is
    unchanged."""
    discipline = AnalyticDiscipline({"y": "x+1"})
    discipline.default_input_data["x"] = array([2.0])
    file_path = tmp_wd / "input.json"
    file_path.write_text(
        json.dumps({
            "type": "object",
            "properties": {
                "x": {"type": "array", "items": {"type": "number", "minimum": 0.0}}
            },
        })
    )

    component = DisciplineWrapperComponent(
        LoadCase(name="LC1"), discipline, input_grammar_file=file_path
    )

    grammar = component.input_grammar
    assert isinstance(grammar, JSONGrammar)
    assert grammar is not discipline.input_grammar
    assert grammar.schema["properties"]["x"]["items"]["minimum"] == 0.0  # ruff: ignore[float-equality-comparison]
    assert component.default_input_data["x"][0] == 2.0  # ruff: ignore[float-equality-comparison]
    assert component.execute()["y"][0] == 3.0  # ruff: ignore[float-equality-comparison]
    with pytest.raises(InvalidDataError, match=r"must be bigger than or equal to 0\.0"):
        component.execute({"x": array([-1.0])})
