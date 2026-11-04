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

import logging
from typing import ClassVar

from gemseo.core.discipline import Discipline
from numpy import atleast_1d
from numpy import inf

from vimseo.api import create_model
from vimseo.core.base_discipline_model import BaseDisciplineModel


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


class _SimpleGrammarDiscipline(Discipline):
    """A discipline using a SimpleGrammar, from which no bound can be read."""

    default_grammar_type = Discipline.GrammarType.SIMPLE

    def __init__(self):
        super().__init__()
        self.input_grammar.update_from_names(["x"])
        self.output_grammar.update_from_names(["y"])
        self.default_input_data = {"x": atleast_1d(1.0)}

    def _run(self, input_data):
        return {"y": input_data["x"]}


class _SimpleGrammarModel(BaseDisciplineModel):
    _DISCIPLINE: ClassVar[Discipline] = _SimpleGrammarDiscipline()
    _EXPECTED_LOAD_CASE = "Dummy"


def test_unbounded_model_warns(tmp_wd, caplog):
    """Check that a model whose input bounds cannot be read warns that they are
    infinite (#100)."""
    with caplog.at_level(logging.WARNING):
        model = _SimpleGrammarModel()
    assert "not a JSONGrammar: no input bounds can be read" in caplog.text
    assert model.lower_bounds["x"] == [-inf]
    assert model.upper_bounds["x"] == [inf]
