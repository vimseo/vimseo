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

from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.core.discipline import Discipline
from numpy import atleast_1d
from numpy import exp
from numpy import linspace
from numpy import max as np_max
from numpy import min as np_min

from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import ConstantTrace
from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import LineStyle
from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import Plot
from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import Trace
from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.utilities.curves_generator import expressions_convexity
from vimseo.utilities.curves_generator import expressions_oscillate
from vimseo.utilities.curves_generator import get_history

if TYPE_CHECKING:
    from collections.abc import Sequence


class MockCurvesDiscipline(Discipline):
    """A mock discipline, constituting the main component of the `MockCurves` model."""

    CURVE_NB_POINTS: ClassVar[int] = 100
    """The number of points of the curve."""

    DECREASING_AXIS: ClassVar[bool] = False
    """Whether the abscissa of the curve has decreasing values."""

    def __init__(self):
        super().__init__()
        self.input_grammar.update_from_data({
            "x": atleast_1d(0.0),
            "x_1": atleast_1d(0.0),
        })
        self.output_grammar.update_from_data({
            "y_history": atleast_1d(0.0),
            "x_history": atleast_1d(0.0),
        })
        self.default_input_data = {
            "x": atleast_1d(1.0),
            "x_1": atleast_1d(1.0),
        }

    def _run(self, input_data):
        x_history = linspace(0, 1.0, self.CURVE_NB_POINTS)
        return {
            "y_history": input_data["x"] * x_history + input_data["x_1"],
            "x_history": x_history,
        }


class MockCurves(BaseDisciplineModel):
    """A toy model whose outputs illustrate the definition of figures holding a single
    line."""

    PLOTS: ClassVar[Sequence[tuple[str, ...]]] = [("x_history", "y_history")]

    _DISCIPLINE: ClassVar[Discipline] = MockCurvesDiscipline()

    _EXPECTED_LOAD_CASE = "Dummy"


class MockCurvesOverride(BaseDisciplineModel):
    """A mock model whose PLOTS are partly overridden/completed by its load case."""

    PLOTS: ClassVar[Sequence[Plot | tuple[str, ...]]] = [
        ("x_history", "y_history"),  # overridden in place by DummyOverride's plot
    ]

    _DISCIPLINE: ClassVar[Discipline] = MockCurvesDiscipline()
    _EXPECTED_LOAD_CASE = "DummyOverride"


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
        x_history = get_history(
            support=linspace(
                input_data["x_left"][0], input_data["x_right"][0], self.CURVE_NB_POINTS
            )
        )
        y_history = get_history(
            list_expressions=[
                expressions_convexity["convex"],
                expressions_oscillate["half_drop"],
            ],
            support=x_history,
        )
        return {
            "x_history": x_history,
            "y_history": y_history
            * input_data["y_max"][0]
            / (np_max(y_history) - np_min(y_history)),
            "x_left": input_data["x_left"],
            "x_right": input_data["x_right"],
        }


class MockCurvesXRange(BaseDisciplineModel):
    PLOTS: ClassVar[Sequence[tuple[str, ...]]] = [("x_history", "y_history")]

    _DISCIPLINE = MockCurvesXRangeDiscipline()
    _EXPECTED_LOAD_CASE = "Dummy"


class MockMultiCurvesDiscipline(Discipline):
    """A mock discipline, constituting the main component of the `MockMultiCurves` model.

    It outputs the histories of a fictitious crack propagation.
    """

    CURVE_NB_POINTS: ClassVar[int] = 50
    """The length of the histories."""

    def __init__(self):
        super().__init__()
        self.input_grammar.update_from_data({
            "max_displacement": atleast_1d(0.0),
            "critical_crack_position": atleast_1d(0.0),
        })
        self.output_grammar.update_from_data({
            "displacement_history": atleast_1d(0.0),
            "energy_strain_history": atleast_1d(0.0),
            "energy_damage_history": atleast_1d(0.0),
            "energy_viscous_history": atleast_1d(0.0),
            "energy_work_history": atleast_1d(0.0),
            "force_history": atleast_1d(0.0),
            "crack_position_history": atleast_1d(0.0),
            "critical_crack_position": atleast_1d(0.0),
        })
        self.default_input_data = {
            "max_displacement": atleast_1d(10.0),
            "critical_crack_position": atleast_1d(35.0),
        }

    def _run(self, input_data):
        displacement = linspace(
            0.0, input_data["max_displacement"][0], self.CURVE_NB_POINTS
        )
        strain = 0.5 * displacement**2
        damage = 0.2 * displacement**1.5
        viscous = 0.05 * displacement
        return {
            "displacement_history": displacement,
            "energy_strain_history": strain,
            "energy_damage_history": damage,
            "energy_viscous_history": viscous,
            "energy_work_history": strain + damage + viscous,
            "force_history": displacement * exp(-0.2 * displacement),
            "crack_position_history": 20.0 + 3.0 * displacement,
            "critical_crack_position": input_data["critical_crack_position"],
        }


class MockMultiCurves(BaseDisciplineModel):
    """A toy model whose outputs illustrate the definition of figures holding several
    lines."""

    SUMMARY = (
        "A toy model whose outputs illustrate figures with several lines, "
        "custom line styles, a secondary y-axis and horizontal reference lines."
    )

    PLOTS: ClassVar[Sequence[Plot | tuple[str, ...]]] = [
        # Several ordinates sharing an axis.
        Plot(
            x="displacement_history",
            traces=[
                Trace("energy_strain_history"),
                Trace("energy_damage_history"),
                Trace("energy_viscous_history"),
            ],
            x_label="Displacement",
        ),
        # A styled figure with a secondary ordinate axis and a reference line.
        Plot(
            x="displacement_history",
            traces=[
                Trace(
                    "force_history",
                    label="force",
                    style=LineStyle(color="blue", marker="."),
                ),
                Trace(
                    "crack_position_history",
                    label="crack position",
                    secondary_y=True,
                    style=LineStyle(color="red", dash="dash"),
                ),
                ConstantTrace(
                    value="critical_crack_position",
                    label="critical crack position",
                    secondary_y=True,
                    style=LineStyle(color="black", dash="dot"),
                ),
            ],
            title="Crack propagation",
            x_label="Displacement",
            y_label="Force",
            y_label_secondary="Crack position",
        ),
    ]

    _DISCIPLINE = MockMultiCurvesDiscipline()
    _EXPECTED_LOAD_CASE = "Dummy"
