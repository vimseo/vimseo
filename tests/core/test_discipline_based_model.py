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

from gemseo.core.discipline import Discipline
from numpy import atleast_1d

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
