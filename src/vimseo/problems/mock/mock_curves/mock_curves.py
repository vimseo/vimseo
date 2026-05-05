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

from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.core.discipline import Discipline
from numpy import atleast_1d
from numpy import linspace
from numpy import max as np_max
from numpy import min as np_min

from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.utilities.curves_generator import expressions_convexity
from vimseo.utilities.curves_generator import expressions_oscillate
from vimseo.utilities.curves_generator import get_history

if TYPE_CHECKING:
    from collections.abc import Sequence


class MockCurvesDiscipline(Discipline):
    """A mock model that outputs a curve depending on an input."""

    CURVE_NB_POINTS: ClassVar[int] = 100
    """The length of the x and y curve."""

    DECREASING_AXIS: ClassVar[bool] = False
    """Whether the abscissa of the y curve has decreasing values."""

    def __init__(self):
        super().__init__()
        self.input_grammar.update_from_data({
            "x": atleast_1d(0.0),
            "x_1": atleast_1d(0.0),
        })
        self.output_grammar.update_from_data({
            "y": atleast_1d(0.0),
            "y_axis": atleast_1d(0.0),
        })
        self.default_input_data = {
            "x": atleast_1d(1.0),
            "x_1": atleast_1d(1.0),
        }

    def _run(self, input_data):
        y_axis = linspace(0, 1.0, self.CURVE_NB_POINTS)
        return {"y": input_data["x"] * y_axis + input_data["x_1"], "y_axis": y_axis}


class MockCurves(BaseDisciplineModel):
    CURVES: ClassVar[Sequence[tuple[str]]] = [("y_axis", "y")]

    _DISCIPLINE: ClassVar[Discipline] = MockCurvesDiscipline()

    _EXPECTED_LOAD_CASE = "Dummy"


class MockCurvesXRangeDiscipline(Discipline):
    """A discipline returning curves whose abscissa range is controlled by its inputs."""

    CURVE_NB_POINTS: ClassVar[int] = 100

    auto_detect_grammar_files = True
    default_grammar_type = Discipline.GrammarType.JSON

    def __init__(self):
        super().__init__()

        self.load_case = "Dummy"
        self.default_input_data = {
            "x_left": atleast_1d(-0.5),
            "x_right": atleast_1d(0.5),
            "y_max": atleast_1d(1.0),
        }

    def _run(self, input_data):
        y_axis = get_history(
            support=linspace(
                input_data["x_left"][0], input_data["x_right"][0], self.CURVE_NB_POINTS
            )
        )
        y = get_history(
            list_expressions=[
                expressions_convexity["convex"],
                expressions_oscillate["half_drop"],
            ],
            support=y_axis,
        )
        return {
            "y_axis": y_axis,
            "y": y * input_data["y_max"][0] / (np_max(y) - np_min(y)),
            "x_left": input_data["x_left"],
            "x_right": input_data["x_right"],
        }


class MockCurvesXRange(BaseDisciplineModel):
    CURVES: ClassVar[Sequence[tuple[str]]] = [("y_axis", "y")]

    _DISCIPLINE = MockCurvesXRangeDiscipline()
    _EXPECTED_LOAD_CASE = "Dummy"
