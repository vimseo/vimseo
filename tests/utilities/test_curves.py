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

from pathlib import Path
from re import escape

import pytest
from numpy import atleast_1d
from numpy import linspace
from numpy import zeros
from numpy.testing import assert_array_equal

from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import ConstantTrace
from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import Plot
from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import Trace
from vimseo.utilities.curves import Curve
from vimseo.utilities.curves import CurveSet
from vimseo.utilities.curves import _resolve_constants


def test_curves(tmp_wd):
    """Check that a curve can be exported as a dictionary and plotted."""

    x = linspace(0, 1, 10)
    curve = Curve({"x": x, "y": 0.5 * x})
    curve_as_dict = curve.as_dict()
    assert_array_equal(curve_as_dict["x"], x)
    assert_array_equal(curve_as_dict["y"], 0.5 * x)

    curve.plot(save=True, show=False)
    assert Path("curve_y_vs_x.html").is_file()


@pytest.mark.parametrize(
    "value",
    [
        zeros((10,)),
        [0] * 10,
    ],
)
def test_curve_axis_update(value):
    """Check that the x and y axis of a curve can be set."""
    x = linspace(0, 1, 10)
    curve = Curve({"x": x, "y": 0.5 * x})
    curve.x = value
    curve.y = value


@pytest.mark.parametrize("value", [[0.0, 1.0], zeros((10, 1)), zeros((10, 2))])
def test_wrong_curve_axis_update(value):
    """Check that the x and y axis of a curve can be set."""
    x = linspace(0, 1, 10)
    curve = Curve({"x": x, "y": 0.5 * x})
    msg = "X axis should be an array of dimension 1 and length 10."
    with pytest.raises(ValueError, match=escape(msg)):
        curve.x = value
    msg = "Y axis should be an array of dimension 1 and length 10."
    with pytest.raises(ValueError, match=escape(msg)):
        curve.y = value


def test_resolve_constants_resolves_string_value_from_data():
    """A constant trace naming a variable is resolved to its scalar value."""
    y0_trace = Trace(y="y0")
    spec = Plot(x="x", traces=[y0_trace, ConstantTrace(value="crit")])
    x = linspace(0, 1, 5)
    data = {"x": x, "y0": x, "crit": atleast_1d(0.5)}

    resolved = _resolve_constants(spec, data)

    assert resolved[0] is y0_trace
    constant = resolved[1]
    assert isinstance(constant, ConstantTrace)
    assert isinstance(constant.value, float)
    assert constant.value == pytest.approx(0.5)
    assert constant.label == "crit"


def test_resolve_constants_keeps_numeric_value_and_explicit_label():
    """An already-numeric constant trace is left untouched."""
    trace = ConstantTrace(value=1.5, label="explicit")
    spec = Plot(x="x", traces=[trace])
    x = linspace(0, 1, 5)

    resolved = _resolve_constants(spec, {"x": x})

    assert resolved == [trace]
    assert resolved[0] is trace


def test_curve_set_from_data_builds_one_curve_per_variable_trace():
    x = linspace(0, 1, 5)
    y0 = x * 2
    y1 = x * 3
    spec = Plot(x="x", traces=[Trace(y="y0"), Trace(y="y1")])

    curve_set = CurveSet.from_data(spec, {"x": x, "y0": y0, "y1": y1})

    assert len(curve_set) == 2
    assert curve_set.ordinate_names == ["y0", "y1"]
    assert_array_equal(curve_set.curves[0].x, x)
    assert_array_equal(curve_set.curves[0].y, y0)
    assert_array_equal(curve_set.curves[1].y, y1)


def test_curve_set_from_data_resolves_constant_traces():
    x = linspace(0, 1, 5)
    y0 = x * 2
    spec = Plot(x="x", traces=[Trace(y="y0"), ConstantTrace(value="crit")])

    curve_set = CurveSet.from_data(spec, {"x": x, "y0": y0, "crit": atleast_1d(0.5)})

    constant = curve_set.spec.traces[-1]
    assert isinstance(constant.value, float)
    assert constant.value == pytest.approx(0.5)


def test_curve_set_from_curve():
    x = linspace(0, 1, 5)
    curve = Curve({"x": x, "y0": x * 2})

    curve_set = CurveSet.from_curve(curve)

    assert curve_set.spec == Plot(x="x", traces=[Trace(y="y0")])
    assert curve_set.curves == [curve]


def test_curve_set_length_mismatch_raises():
    x = linspace(0, 1, 5)
    spec = Plot(x="x", traces=[Trace(y="y0"), Trace(y="y1")])
    curve = Curve({"x": x, "y0": x})
    msg = (
        "The number of curves (1) shall match the number of variable traces "
        "of the plot (2)."
    )
    with pytest.raises(ValueError, match=escape(msg)):
        CurveSet(spec, [curve])


def test_curve_set_select_returns_matching_curve():
    x = linspace(0, 1, 5)
    spec = Plot(x="x", traces=[Trace(y="y0"), Trace(y="y1")])
    curve0 = Curve({"x": x, "y0": x})
    curve1 = Curve({"x": x, "y1": x * 2})

    curve_set = CurveSet(spec, [curve0, curve1])

    assert curve_set.select("y1") is curve1


def test_curve_set_select_unknown_ordinate_raises():
    x = linspace(0, 1, 5)
    spec = Plot(x="x", traces=[Trace(y="y0")])
    curve_set = CurveSet(spec, [Curve({"x": x, "y0": x})])

    with pytest.raises(KeyError, match="There is no curve of ordinate y1"):
        curve_set.select("y1")


def test_curve_set_x_range():
    spec = Plot(x="x", traces=[Trace(y="y0"), Trace(y="y1")])
    curve0 = Curve({"x": linspace(0, 5, 5), "y0": linspace(0, 5, 5)})
    curve1 = Curve({"x": linspace(1, 8, 5), "y1": linspace(1, 8, 5)})

    curve_set = CurveSet(spec, [curve0, curve1])

    assert curve_set.x_range == (0.0, 8.0)


def test_curve_set_len_and_iter():
    x = linspace(0, 1, 5)
    spec = Plot(x="x", traces=[Trace(y="y0"), Trace(y="y1")])
    curves = [Curve({"x": x, "y0": x}), Curve({"x": x, "y1": x})]

    curve_set = CurveSet(spec, curves)

    assert len(curve_set) == 2
    assert list(curve_set) == curves


def test_curve_set_str():
    x = linspace(0, 1, 5)
    spec = Plot(x="x", traces=[Trace(y="y0"), Trace(y="y1")])
    curve_set = CurveSet(spec, [Curve({"x": x, "y0": x}), Curve({"x": x, "y1": x})])

    lines = str(curve_set).splitlines()

    assert lines[0] == f"Plot {spec.get_name()}:"
    assert "y0 vs x" in lines
    assert "y1 vs x" in lines


def test_curve_set_plot_delegates_to_superpose_curves(tmp_wd):
    """``CurveSet.plot`` renders through ``superpose_curves``."""
    x = linspace(0, 1, 5)
    spec = Plot(x="x", traces=[Trace(y="y0")])
    curve_set = CurveSet(spec, [Curve({"x": x, "y0": x * 2})])

    curve_set.plot(save=True, show=False)

    assert Path(spec.get_file_name()).is_file()
