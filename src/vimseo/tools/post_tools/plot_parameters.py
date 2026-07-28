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

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any

from docstring_inheritance import GoogleDocstringInheritanceMeta

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

DEFAULT_AXIS_COLOR = "black"
"""The colour of an ordinate axis holding more than one trace."""


@dataclass
class LineStyle(metaclass=GoogleDocstringInheritanceMeta):
    """The style of a single line of a plot.

    Any attribute left to ``None`` is resolved at rendering time, either from a
    default palette or from the plotting library defaults.
    """

    color: str | None = None
    """The colour of the line, e.g. ``"green"`` or ``"#1f77b4"``."""

    dash: str | None = None
    """The dash pattern, e.g. ``"solid"``, ``"dash"``, ``"dot"`` or ``"dashdot"``."""

    width: float | None = None
    """The width of the line."""

    marker: str | None = None
    """The marker symbol, e.g. ``"circle"`` or ``"x"``.

    When ``None``, the line is drawn without markers.
    """


@dataclass
class Trace(metaclass=GoogleDocstringInheritanceMeta):
    """A single line of a plot, defined from the model variable names."""

    y: str
    """The name of the ordinate variable."""

    x: str | None = None
    """The name of the abscissa variable.

    When ``None``, the abscissa of the parent :class:`.Plot` is used.
    """

    label: str = ""
    """The legend entry of the line. Defaults to the ordinate variable name."""

    secondary_y: bool = False
    """Whether the line is drawn against the secondary (right) ordinate axis."""

    style: LineStyle = field(default_factory=LineStyle)
    """The style of the line."""

    def get_label(self) -> str:
        """Return the legend entry, falling back to the ordinate variable name."""
        return self.label or self.y


@dataclass
class ConstantTrace(metaclass=GoogleDocstringInheritanceMeta):
    """A horizontal reference line spanning the abscissa range of a plot.

    Useful to compare an output history against an input value, e.g. the critical
    energy release rate prescribed as a model input.
    """

    value: float | str
    """The ordinate value of the horizontal line.

    A string is the name of a scalar model variable, whose value is resolved when
    the plot is built from the model data. This is the usual case, e.g. to draw a
    material property prescribed as a model input.
    """

    label: str = ""
    """The legend entry of the line. Defaults to the variable name or the value."""

    secondary_y: bool = False
    """Whether the line is drawn against the secondary (right) ordinate axis."""

    style: LineStyle = field(default_factory=LineStyle)
    """The style of the line."""

    def get_label(self) -> str:
        """Return the legend entry, falling back to the ordinate value."""
        return self.label or str(self.value)


TraceType = Trace | ConstantTrace
"""Any kind of line that a :class:`.Plot` can hold."""


@dataclass
class Plot(metaclass=GoogleDocstringInheritanceMeta):
    """The declarative definition of a figure holding one or several lines.

    This is a specification: it holds variable *names*, not data. It is therefore
    serialisable, and can be declared either as the class attribute ``PLOTS`` of a
    model or in the JSON file of a load case.

    Examples:
        >>> Plot(
        ...     x="displacement_history",
        ...     traces=[
        ...         Trace(
        ...             "energy_strain_history",
        ...             label="strain",
        ...             style=LineStyle(color="green"),
        ...         ),
        ...         Trace(
        ...             "energy_damage_history",
        ...             label="damage",
        ...             style=LineStyle(color="red"),
        ...         ),
        ...     ],
        ...     title="Energy balance evolution",
        ... )
    """

    x: str
    """The name of the abscissa variable shared by the traces."""

    traces: list[TraceType] = field(default_factory=list)
    """The lines of the figure."""

    title: str = ""
    """The title of the figure."""

    y_label: str = ""
    """The label of the primary ordinate axis. Defaults to the variable names."""

    y_label_secondary: str = ""
    """The label of the secondary ordinate axis. Defaults to the variable names."""

    file_name: str = ""
    """The name of the file to save the figure to. Defaults to :meth:`.get_name`."""

    @classmethod
    def from_variable_names(cls, variable_names: tuple[str, ...]) -> Plot:
        """Create a plot from a tuple of variable names.

        The first name is the abscissa, the remaining ones are the ordinates, each
        drawn as a line against the primary axis with a default style.

        Args:
            variable_names: The abscissa name followed by at least one ordinate name.

        Returns:
            The plot.

        Raises:
            ValueError: When fewer than two names are given.
        """
        if len(variable_names) < 2:
            msg = (
                f"A plot shall be defined from at least an abscissa and an ordinate "
                f"variable name, but got {variable_names}."
            )
            raise ValueError(msg)
        return cls(
            x=variable_names[0],
            traces=[Trace(y=name) for name in variable_names[1:]],
        )

    @property
    def variable_traces(self) -> list[Trace]:
        """The traces bound to a model variable, excluding the constant ones."""
        return [trace for trace in self.traces if isinstance(trace, Trace)]

    @property
    def variable_names(self) -> list[str]:
        """The names of all the model variables involved in the plot."""
        names = [self.x]
        for trace in self.variable_traces:
            for name in (trace.x or self.x, trace.y):
                if name not in names:
                    names.append(name)
        return names

    def get_abscissa_name(self, trace: Trace) -> str:
        """Return the abscissa name of a trace, falling back to the plot abscissa."""
        return trace.x or self.x

    def get_name(self) -> str:
        """Return a name for the figure, used as a figure key and as a file name.

        The name is derived from the title when there is one. Otherwise it is
        derived from the variable names, in which case only the first ordinate is
        used, so that the name of a figure holding many lines stays short enough
        for the file systems limiting the length of the paths.
        """
        if self.title:
            return self.title.lower().replace(" ", "_")
        ordinates = self.variable_traces
        name = ordinates[0].y if ordinates else ""
        if len(ordinates) > 1:
            name = f"{name}_and_{len(ordinates) - 1}_more"
        return f"{name}_vs_{self.x}"

    def get_file_name(self, extension: str = "html") -> str:
        """Return the name of the file to save the figure to."""
        return self.file_name or f"{self.get_name()}.{extension}"


def create_trace(definition: TraceType | Mapping[str, Any]) -> TraceType:
    """Create a trace from its definition.

    Args:
        definition: Either a trace, or a mapping of its attributes, e.g. read from
            the JSON file of a load case. A mapping holding a ``"value"`` entry
            defines a :class:`.ConstantTrace`, otherwise a :class:`.Trace`.

    Returns:
        The trace.
    """
    if isinstance(definition, (Trace, ConstantTrace)):
        return definition
    definition = dict(definition)
    style = definition.pop("style", {})
    if not isinstance(style, LineStyle):
        style = LineStyle(**style)
    if "value" in definition:
        return ConstantTrace(style=style, **definition)
    return Trace(style=style, **definition)


def create_plot(definition: Plot | Sequence[str] | Mapping[str, Any]) -> Plot:
    """Create a plot from its definition.

    Args:
        definition: Either a plot, a sequence of variable names whose first one is
            the abscissa, or a mapping of the plot attributes, e.g. read from the
            JSON file of a load case.

    Returns:
        The plot.
    """
    if isinstance(definition, Plot):
        return definition
    if isinstance(definition, (list, tuple)):
        return Plot.from_variable_names(tuple(definition))
    definition = dict(definition)
    traces = [create_trace(trace) for trace in definition.pop("traces", [])]
    return Plot(traces=traces, **definition)


@dataclass
class PlotParameters(metaclass=GoogleDocstringInheritanceMeta):
    """The parameters of a model plot."""

    plots: list[Plot] = field(default_factory=list)
    """The definitions of the figures."""
