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

import pytest
from numpy import linspace
from plotly.graph_objs import Figure

from vimseo.tools.post_tools.plot_parameters import DEFAULT_AXIS_COLOR
from vimseo.tools.post_tools.plot_parameters import ConstantTrace
from vimseo.tools.post_tools.plot_parameters import LineStyle
from vimseo.tools.post_tools.plot_parameters import Plot
from vimseo.tools.post_tools.plot_parameters import Trace
from vimseo.utilities.curves import Curve
from vimseo.utilities.curves import CurveSet
from vimseo.utilities.plotting_utils import COLORS
from vimseo.utilities.plotting_utils import DASHES
from vimseo.utilities.plotting_utils import LINE_WIDTH
from vimseo.utilities.plotting_utils import MARKER_SIZE
from vimseo.utilities.plotting_utils import _set_ordinate_axis
from vimseo.utilities.plotting_utils import superpose_curves


def _curve_set(x, ordinates, *, traces=None, **plot_kwargs):
    """Build a CurveSet directly from raw arrays, without going through a model."""
    if traces is None:
        traces = [Trace(y=name) for name in ordinates]
    spec = Plot(x="x", traces=traces, **plot_kwargs)
    curves = [
        Curve({"x": x, trace.y: ordinates[trace.y]}) for trace in spec.variable_traces
    ]
    return CurveSet(spec, curves)


def test_superpose_curves_single_curve_set():
    """A single curve set draws its traces with the default colour palette."""
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x, "y1": x * 2})

    fig = superpose_curves(curve_set, show=False)

    assert [trace.name for trace in fig.data] == ["y0", "y1"]
    assert [trace.line.color for trace in fig.data] == [COLORS[0], COLORS[1]]
    # A single ordinate axis holding several lines takes the default colour.
    assert fig.layout.yaxis.title.font.color == DEFAULT_AXIS_COLOR


def test_superpose_curves_multi_source_uses_source_colour_and_variable_dash():
    """Colour identifies the source, dash pattern identifies the variable."""
    x = linspace(0, 1, 5)
    cs1 = _curve_set(x, {"y0": x, "y1": x * 2})
    cs2 = _curve_set(x, {"y0": x * 3, "y1": x * 4})

    fig = superpose_curves([cs1, cs2], labels=["Run A", "Run B"], show=False)

    assert [trace.name for trace in fig.data] == [
        "Run A - y0",
        "Run A - y1",
        "Run B - y0",
        "Run B - y1",
    ]
    assert fig.data[0].line.color == fig.data[1].line.color == COLORS[0]
    assert fig.data[2].line.color == fig.data[3].line.color == COLORS[1]
    assert fig.data[0].line.dash == fig.data[2].line.dash == DASHES[0]
    assert fig.data[1].line.dash == fig.data[3].line.dash == DASHES[1]


def test_superpose_curves_secondary_axis():
    """A trace flagged ``secondary_y`` is drawn against the secondary axis."""
    x = linspace(0, 1, 5)
    traces = [Trace(y="y0"), Trace(y="y1", secondary_y=True)]
    curve_set = _curve_set(x, {"y0": x, "y1": x * 2}, traces=traces)

    fig = superpose_curves(curve_set, show=False)

    assert [trace.yaxis for trace in fig.data] == ["y", "y2"]
    assert fig.layout.yaxis2 is not None


def test_superpose_curves_constant_trace_spans_x_range():
    """A resolved constant trace is drawn as a flat line over the abscissa range."""
    x = linspace(0, 2, 5)
    traces = [Trace(y="y0"), ConstantTrace(value=2.5)]
    curve_set = _curve_set(x, {"y0": x}, traces=traces)

    fig = superpose_curves(curve_set, show=False)

    constant_trace = fig.data[1]
    assert list(constant_trace.x) == [0.0, 2.0]
    assert list(constant_trace.y) == [2.5, 2.5]


def test_superpose_curves_variable_names_filters_traces():
    """Selecting variables keeps only the matching traces, plus the constants."""
    x = linspace(0, 1, 5)
    traces = [Trace(y="y0"), Trace(y="y1"), Trace(y="y2"), ConstantTrace(value=1.0)]
    curve_set = _curve_set(x, {"y0": x, "y1": x * 2, "y2": x * 3}, traces=traces)

    fig = superpose_curves(curve_set, variable_names=["y0"], show=False)

    assert [trace.name for trace in fig.data] == ["y0", "1.0"]


def test_check_abscissa_names_mismatch_raises():
    """Superposing sources with different abscissa variables is rejected."""
    x = linspace(0, 1, 5)
    cs1 = _curve_set(x, {"y0": x})
    spec2 = Plot(x="t", traces=[Trace(y="y0")])
    cs2 = CurveSet(spec2, [Curve({"t": x, "y0": x})])

    with pytest.raises(ValueError, match="Abscissa names are not unique"):
        superpose_curves([cs1, cs2], show=False)


def test_line_style_width_override():
    """A prescribed line width overrides the default width."""
    x = linspace(0, 1, 5)
    traces = [Trace(y="y0", style=LineStyle(width=4.0))]
    curve_set = _curve_set(x, {"y0": x}, traces=traces)

    fig = superpose_curves(curve_set, show=False)

    assert fig.data[0].line.width == pytest.approx(4.0)


def test_line_style_width_and_marker_size_defaults():
    """Without a prescribed width, the VIMSEO default width and marker size apply."""
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x})

    fig = superpose_curves(curve_set, show=False)

    assert fig.data[0].line.width == pytest.approx(LINE_WIDTH)
    assert fig.data[0].marker.size == pytest.approx(MARKER_SIZE)


def test_set_ordinate_axis_no_colors_is_a_noop():
    """An axis with no traces (no colours to resolve) is left untouched."""
    fig = Figure()

    _set_ordinate_axis(fig, "label", [], secondary_y=True, has_secondary=True)

    assert fig.layout.yaxis.title.text is None


def test_superpose_curves_fig_reuse():
    """A figure passed through ``fig=`` is reused and accumulates traces."""
    x = linspace(0, 1, 5)
    cs1 = _curve_set(x, {"y0": x})
    cs2 = _curve_set(x, {"y1": x * 2})

    fig1 = superpose_curves(cs1, show=False)
    fig2 = superpose_curves(cs2, fig=fig1, show=False)

    assert fig2 is fig1
    assert len(fig1.data) == 2


def test_superpose_curves_no_sources_spec_is_none():
    """Superposing no sources at all does not raise, and draws nothing."""
    fig = superpose_curves([], show=False)

    assert list(fig.data) == []


def test_superpose_curves_save_creates_missing_directory(tmp_wd):
    """Saving to a directory that does not exist yet creates it."""
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x})

    superpose_curves(
        curve_set,
        save=True,
        show=False,
        directory_path="new_subdir",
        file_name="out.html",
    )

    assert Path("new_subdir/out.html").is_file()


def test_superpose_curves_save_default_directory(tmp_wd):
    """Saving with the default directory and file name writes ``curves.html``."""
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x})

    superpose_curves(curve_set, save=True, show=False)

    assert Path("curves.html").is_file()


def test_superpose_curves_show_calls_fig_show(monkeypatch):
    """``show=True`` renders the figure through Plotly's own ``show``."""
    calls = []
    monkeypatch.setattr(Figure, "show", lambda self, *a, **k: calls.append(1))
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x})

    superpose_curves(curve_set, show=True, save=False)

    assert calls == [1]


def test_superpose_curves_show_false_does_not_call_fig_show(monkeypatch):
    """``show=False`` never calls Plotly's ``show``."""
    calls = []
    monkeypatch.setattr(Figure, "show", lambda self, *a, **k: calls.append(1))
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x})

    superpose_curves(curve_set, show=False, save=False)

    assert calls == []


def test_superpose_curves_default_axis_labels_join_names():
    """Without an explicit axis label, the variable names are joined."""
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x, "y1": x * 2})

    fig = superpose_curves(curve_set, show=False)

    assert fig.layout.yaxis.title.text == "y0, y1"


def test_superpose_curves_title_applied_when_set():
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x}, title="My title")

    fig = superpose_curves(curve_set, show=False)

    assert fig.layout.title.text == "My title"


def test_superpose_curves_no_title_leaves_layout_title_unset():
    x = linspace(0, 1, 5)
    curve_set = _curve_set(x, {"y0": x})

    fig = superpose_curves(curve_set, show=False)

    assert fig.layout.title.text is None
