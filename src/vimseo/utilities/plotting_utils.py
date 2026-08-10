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

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from numpy import array_str
from numpy import atleast_1d
from plotly.graph_objs import Figure
from plotly.graph_objs import Scatter
from plotly.subplots import make_subplots

from vimseo.tools.post_tools.plot_parameters import DEFAULT_AXIS_COLOR
from vimseo.tools.post_tools.plot_parameters import ConstantTrace
from vimseo.utilities.curves import Curve
from vimseo.utilities.curves import CurveSet

if TYPE_CHECKING:
    from collections.abc import Iterable

    from vimseo.tools.post_tools.plot_parameters import LineStyle
    from vimseo.tools.post_tools.plot_parameters import TraceType

FLOAT_PRECISION = 3

LINE_WIDTH = 2
"""The line width used when a trace does not prescribe one."""

MARKER_SIZE = 4
"""The marker size used when a trace does not prescribe one."""

COLORS = ("blue", "red", "green", "black", "orange", "purple", "brown", "cyan")
"""The colours used when a trace does not prescribe one."""

DASHES = ("solid", "dash", "dot", "dashdot")
"""The dash patterns used to distinguish the traces of superposed sources."""

DASH_ALIASES = {"-": "solid", "--": "dash", "-.": "dashdot", ":": "dot", "..": "dot"}
"""The Matplotlib dash patterns mapped to their Plotly counterparts."""

MARKER_ALIASES = {
    ".": "circle",
    "o": "circle",
    "x": "x",
    "+": "cross",
    "s": "square",
    "^": "triangle-up",
    "v": "triangle-down",
    "*": "star",
    "d": "diamond",
}
"""The Matplotlib marker symbols mapped to their Plotly counterparts."""


def _as_curve_sets(sources) -> list[CurveSet]:
    """Normalise the sources of a superposition into a list of curve sets."""
    if isinstance(sources, (CurveSet, Curve)):
        sources = [sources]
    return [
        CurveSet.from_curve(source) if isinstance(source, Curve) else source
        for source in sources
    ]


def _select_variables(curve_set: CurveSet, variable_names: Iterable[str]) -> CurveSet:
    """Return a curve set restricted to some ordinate variables.

    The constant traces are always kept, since they are reference lines.
    """
    traces = [
        trace
        for trace in curve_set.spec.traces
        if isinstance(trace, ConstantTrace) or trace.y in variable_names
    ]
    curves = [
        curve
        for trace, curve in zip(
            curve_set.spec.variable_traces, curve_set.curves, strict=True
        )
        if trace.y in variable_names
    ]
    return CurveSet(replace(curve_set.spec, traces=traces), curves)


def _resolve_color(
    style: LineStyle, source_index: int, trace_index: int, n_sources: int
) -> str:
    """Return the colour of a trace, from its style or from the default palette.

    When several sources are superposed, the colour identifies the source, so that
    a given variable keeps the same colour across the sources.
    """
    if style.color is not None:
        return style.color
    index = source_index if n_sources > 1 else trace_index
    return COLORS[index % len(COLORS)]


def _resolve_dash(style: LineStyle, trace_index: int, n_sources: int) -> str:
    """Return the dash pattern of a trace, from its style or the default palette.

    When several sources are superposed, the dash pattern identifies the variable,
    the colour being already used to identify the source.
    """
    if style.dash is not None:
        return DASH_ALIASES.get(style.dash, style.dash)
    return DASHES[trace_index % len(DASHES)] if n_sources > 1 else "solid"


def _resolve_label(trace: TraceType, source_label: str, n_sources: int) -> str:
    """Return the legend entry of a trace, prefixed by its source when relevant."""
    label = trace.get_label()
    if n_sources > 1 and source_label:
        return f"{source_label} - {label}"
    return label


def _make_scatter(
    x_values, y_values, label: str, style: LineStyle, color: str, dash: str
) -> Scatter:
    """Create a Plotly line from the values of a trace and its resolved style."""
    line = {"color": color, "dash": dash, "width": style.width or LINE_WIDTH}
    return Scatter(
        x=x_values,
        y=y_values,
        name=label,
        mode="lines+markers" if style.marker else "lines",
        line=line,
        marker={
            "symbol": MARKER_ALIASES.get(style.marker, style.marker),
            "color": color,
            "size": MARKER_SIZE,
        },
    )


def _check_abscissa_names(curve_sets: Iterable[CurveSet]) -> None:
    """Check that all the superposed traces share the same abscissa variable.

    Raises:
        ValueError: When the abscissa names are not unique.
    """
    abscissa_names = [
        curve_set.spec.get_abscissa_name(trace)
        for curve_set in curve_sets
        for trace in curve_set.spec.variable_traces
    ]
    if abscissa_names and abscissa_names.count(abscissa_names[0]) != len(
        abscissa_names
    ):
        msg = f"Abscissa names are not unique: {abscissa_names}"
        raise ValueError(msg)


def _set_ordinate_axis(
    fig: Figure,
    label: str,
    colors: list[str],
    secondary_y: bool,
    has_secondary: bool,
) -> None:
    """Set the title and colour of an ordinate axis.

    The axis takes the colour of its trace when it holds a single one, and the
    default colour otherwise.

    The ``secondary_y`` selector is only understood by the figures created with
    secondary axis support, hence it is only passed when such an axis exists.
    """
    if not colors:
        return
    options = {
        "title_text": label,
        "title_font_color": colors[0] if len(colors) == 1 else DEFAULT_AXIS_COLOR,
    }
    options["tickfont_color"] = options["title_font_color"]
    if has_secondary:
        options["secondary_y"] = secondary_y
    fig.update_yaxes(**options)


def superpose_curves(
    sources: CurveSet | Curve | Iterable[CurveSet | Curve],
    variable_names: Iterable[str] = (),
    labels: Iterable[str] = (),
    directory_path: str | Path = "",
    save: bool = False,
    show: bool = True,
    file_name: str | Path = "",
    fig: Figure | None = None,
) -> Figure:
    """Superpose curves on a single figure.

    The curves are given either individually, or bundled into the
    :class:`.CurveSet` of a figure, which also carries their style.
    This handles the two kinds of superposition:

    - the traces of a single :class:`.CurveSet`, i.e. several ordinate variables of
      a single model result, styled by its plot specification,
    - the same curve coming from several results, e.g. to compare the runs of a
      database, in which case ``labels`` identifies each result.

    Args:
        sources: The curve sets or curves to draw.
            They shall all share the same abscissa variable.
        variable_names: The names of the ordinate variables to draw.
            All of them by default.
        labels: The label of each source, used as a legend prefix.
        directory_path: The path where to save the figure.
        save: Whether to save the figure.
        show: Whether to show the figure.
        file_name: The name of the file to save the figure to.
        fig: A figure to draw on. A new one is created when ``None``.

    Returns:
        The figure.

    Raises:
        ValueError: When the sources do not share the same abscissa variable.
    """
    curve_sets = _as_curve_sets(sources)
    labels = list(labels)

    variable_names = list(variable_names)
    if variable_names:
        curve_sets = [
            _select_variables(curve_set, variable_names) for curve_set in curve_sets
        ]

    _check_abscissa_names(curve_sets)

    n_sources = len(curve_sets)
    spec = curve_sets[0].spec if curve_sets else None
    has_secondary = any(
        trace.secondary_y for curve_set in curve_sets for trace in curve_set.spec.traces
    )

    if fig is None:
        fig = (
            make_subplots(specs=[[{"secondary_y": True}]])
            if has_secondary
            else Figure()
        )

    colors_by_axis = {False: [], True: []}
    names_by_axis = {False: [], True: []}

    for source_index, curve_set in enumerate(curve_sets):
        source_label = labels[source_index] if source_index < len(labels) else ""
        curve_index = 0
        for trace_index, trace in enumerate(curve_set.spec.traces):
            color = _resolve_color(trace.style, source_index, trace_index, n_sources)
            dash = _resolve_dash(trace.style, trace_index, n_sources)
            label = _resolve_label(trace, source_label, n_sources)

            if isinstance(trace, ConstantTrace):
                x_min, x_max = curve_set.x_range
                x_values = [x_min, x_max]
                y_values = [trace.value, trace.value]
                ordinate_name = trace.get_label()
            else:
                curve = curve_set.curves[curve_index]
                curve_index += 1
                x_values = curve.x
                y_values = curve.y
                ordinate_name = trace.y

            scatter = _make_scatter(x_values, y_values, label, trace.style, color, dash)
            if has_secondary:
                fig.add_trace(scatter, secondary_y=trace.secondary_y)
            else:
                fig.add_trace(scatter)

            colors_by_axis[trace.secondary_y].append(color)
            if ordinate_name not in names_by_axis[trace.secondary_y]:
                names_by_axis[trace.secondary_y].append(ordinate_name)

    if spec is not None:
        fig.update_xaxes(title_text=spec.x)
        _set_ordinate_axis(
            fig,
            spec.y_label or ", ".join(names_by_axis[False]),
            colors_by_axis[False],
            secondary_y=False,
            has_secondary=has_secondary,
        )
        if has_secondary:
            _set_ordinate_axis(
                fig,
                spec.y_label_secondary or ", ".join(names_by_axis[True]),
                colors_by_axis[True],
                secondary_y=True,
                has_secondary=has_secondary,
            )
        if spec.title:
            fig.update_layout(title_text=spec.title)

    file_name = "curves.html" if file_name == "" else file_name
    if save:
        directory_path = Path(directory_path)
        if str(directory_path) != "." and not directory_path.exists():
            directory_path.mkdir(parents=True)
        fig.write_html(str(directory_path / file_name))
    if show:
        fig.show()

    return fig


def get_formatted_value(value, precision: int = FLOAT_PRECISION):
    """Rounds either a float or a NumPy array.

    Args:
        value: The data to round.
        precision: The rounding precision.

    Returns: The rounded data.
    """
    is_float = isinstance(value, float)
    if is_float:
        return str(round(value, precision))
    return array_str(atleast_1d(value), precision=precision)
