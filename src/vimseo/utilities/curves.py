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
from typing import TYPE_CHECKING

from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.lines import Lines
from numpy import array
from numpy import atleast_1d
from numpy import vstack
from pandas import DataFrame

from vimseo.tools.post_tools.plot_parameters import ConstantTrace
from vimseo.tools.post_tools.plot_parameters import Plot
from vimseo.tools.post_tools.plot_parameters import Trace

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

    from numpy import ndarray
    from plotly.graph_objs import Figure


class Curve:
    """A curve."""

    __names: Iterable[str]
    __data: ndarray | None = None

    def __init__(self, data: Mapping[str, ndarray], abscissa_name=""):
        """Construct the curve from a dictionary of 1D arrays."""
        self.__names = list(data.keys())
        if len(self.__names) != 2:
            msg = (
                f"The curve should be created from a dictionary "
                f"containing exactly two items. But the dictionary "
                f"is {data}."
            )
            raise ValueError(msg)
        if abscissa_name != "":
            i = self.__names.index(abscissa_name)
            self.__names = self.__names[i:] + self.__names[:i]
            data = {name: data[name] for name in self.__names}
        self.__data = vstack(list(data.values()))
        self.__length = len(self.__data[0])

    @property
    def length(self):
        """The length of the x-axis (which is equal to the length of the y-axis)"""
        return self.__length

    @property
    def variable_names(self):
        """The (x,y) names of the variables."""
        return tuple(self.__names)

    @property
    def x(self) -> ndarray:
        return self.__data[0]

    @property
    def y(self) -> ndarray:
        return self.__data[1]

    def __update_axis_check(self, value: ndarray, axis_name: str):
        if value.ndim != 1 or len(value) != self.__length:
            msg = (
                f"{axis_name.upper()} axis should be an array of dimension 1 "
                f"and length {self.__length}."
            )
            raise ValueError(msg)

    @x.setter
    def x(self, value: ndarray):
        value = array(value)
        self.__update_axis_check(value, "X")
        self.__data[0] = value

    @y.setter
    def y(self, value: ndarray):
        value = array(value)
        self.__update_axis_check(value, "Y")
        self.__data[1] = value

    def as_dict(self):
        """The curve as a dictionary."""
        return {
            self.__names[0]: self.__data[0],
            self.__names[1]: self.__data[1],
        }

    def as_dataframe(self):
        """The curve as a ``Pandas.DataFrame``"""
        return DataFrame.from_dict(self.as_dict())

    def __str__(self):
        return self.as_dataframe().T.to_string()

    def plot(
        self,
        directory_path: str | Path = "",
        save=False,
        show=True,
        file_name: str | Path = "",
        fig: Figure | None = None,
        label: str = "",
        **options,
    ):
        """Plot the curve."""
        properties = ["color", "linestyle"]
        dataset = Dataset.from_array(
            self.__data.T,
            variable_names=self.__names,
        )
        file_name = (
            f"curve_{self.__names[1]}_vs_{self.__names[0]}.html"
            if file_name == ""
            else file_name
        )
        plot = Lines(
            dataset,
            abscissa_variable=self.__names[0],
            variables=[self.__names[1]],
        )
        if label != "":
            plot.labels = {self.__names[1]: label}
        for prop in properties:
            if prop in options:
                setattr(plot, prop, options[prop])
        return plot.execute(
            save=save,
            show=show,
            directory_path=directory_path,
            file_name=file_name,
            file_format="html",
            fig=fig,
        )[0]


def _resolve_constants(spec: Plot, data: Mapping[str, ndarray]) -> list:
    """Resolve the constant traces defined from a variable name into their value.

    Args:
        spec: The specification of the figure.
        data: The model data, mapping the variable names to their values.

    Returns:
        The traces of the specification, with the constant ones resolved.
    """
    traces = []
    for trace in spec.traces:
        if isinstance(trace, ConstantTrace) and isinstance(trace.value, str):
            traces.append(
                replace(
                    trace,
                    value=float(atleast_1d(data[trace.value])[0]),
                    label=trace.label or trace.value,
                )
            )
        else:
            traces.append(trace)
    return traces


class CurveSet:
    """The curves of a single figure, together with their plot specification.

    A ``CurveSet`` composes :class:`.Curve` objects, one per variable trace of the
    specification: each curve remains a two-column object on which curve measures
    can be computed, while the set carries the multi-line rendering information.
    """

    spec: Plot
    """The specification of the figure."""

    curves: list[Curve]
    """The curves, one per variable trace of :attr:`.spec`, in the same order."""

    def __init__(self, spec: Plot, curves: Iterable[Curve]) -> None:
        """
        Args:
            spec: The specification of the figure.
            curves: The curves, one per variable trace of ``spec``.

        Raises:
            ValueError: When the number of curves does not match the number of
                variable traces of the specification.
        """
        curves = list(curves)
        if len(curves) != len(spec.variable_traces):
            msg = (
                f"The number of curves ({len(curves)}) shall match the number of "
                f"variable traces of the plot ({len(spec.variable_traces)})."
            )
            raise ValueError(msg)
        self.spec = spec
        self.curves = curves

    @classmethod
    def from_data(cls, spec: Plot, data: Mapping[str, ndarray]) -> CurveSet:
        """Create a curve set from a plot specification and model data.

        Args:
            spec: The specification of the figure.
            data: The model data, mapping the variable names to their values.

        Returns:
            The curve set.
        """
        curves = []
        for trace in spec.variable_traces:
            abscissa_name = spec.get_abscissa_name(trace)
            curves.append(
                Curve(
                    {
                        abscissa_name: data[abscissa_name],
                        trace.y: data[trace.y],
                    },
                    abscissa_name=abscissa_name,
                )
            )
        return cls(replace(spec, traces=_resolve_constants(spec, data)), curves)

    @classmethod
    def from_curve(cls, curve: Curve) -> CurveSet:
        """Create a single-line curve set from a curve."""
        abscissa_name, ordinate_name = curve.variable_names
        return cls(Plot(x=abscissa_name, traces=[Trace(y=ordinate_name)]), [curve])

    def select(self, ordinate_name: str) -> Curve:
        """Return the curve of a given ordinate variable.

        Args:
            ordinate_name: The name of the ordinate variable.

        Returns:
            The curve.

        Raises:
            KeyError: When no curve has this ordinate variable.
        """
        for trace, curve in zip(self.spec.variable_traces, self.curves, strict=True):
            if trace.y == ordinate_name:
                return curve
        msg = (
            f"There is no curve of ordinate {ordinate_name} in this plot. "
            f"Available ordinates are {self.ordinate_names}."
        )
        raise KeyError(msg)

    @property
    def ordinate_names(self) -> list[str]:
        """The names of the ordinate variables."""
        return [trace.y for trace in self.spec.variable_traces]

    @property
    def x_range(self) -> tuple[float, float]:
        """The bounds of the abscissa over all the curves."""
        return (
            min(curve.x.min() for curve in self.curves),
            max(curve.x.max() for curve in self.curves),
        )

    def __len__(self) -> int:
        return len(self.curves)

    def __iter__(self):
        return iter(self.curves)

    def __str__(self) -> str:
        text = [f"Plot {self.spec.get_name()}:"]
        text.extend(
            f"{trace.y} vs {self.spec.get_abscissa_name(trace)}"
            for trace in self.spec.variable_traces
        )
        return "\n".join(text)

    def plot(
        self,
        directory_path: str | Path = "",
        save: bool = False,
        show: bool = True,
        file_name: str | Path = "",
        fig: Figure | None = None,
        variable_names: Iterable[str] = (),
    ) -> Figure:
        """Plot the curves of the set on a single figure.

        Args:
            directory_path: The path where to save the figure.
            save: Whether to save the figure.
            show: Whether to show the figure.
            file_name: The name of the file. Defaults to the plot specification one.
            fig: A figure to draw on. A new one is created when ``None``.
            variable_names: The ordinate names to draw. All of them by default.

        Returns:
            The figure.
        """
        from vimseo.utilities.plotting_utils import superpose_curves

        return superpose_curves(
            self,
            variable_names=variable_names,
            directory_path=directory_path,
            save=save,
            show=show,
            file_name=file_name or self.spec.get_file_name(),
            fig=fig,
        )
