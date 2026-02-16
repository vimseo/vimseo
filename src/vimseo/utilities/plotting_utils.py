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

from collections.abc import Iterable
from typing import TYPE_CHECKING

from numpy import array_str
from numpy import atleast_1d
from plotly.graph_objs import Figure

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.utilities.curves import Curve

FLOAT_PRECISION = 3


def plot_curves(
    curves: Iterable[Curve] | Curve,
    directory_path: str | Path = "",
    save=False,
    show=True,
    file_name: str | Path = "",
    labels: Iterable[str] = (),
) -> Figure:
    # Handle up to 16 curves
    nb_color_period = 4
    colors = ["blue", "red", "green", "black"] * nb_color_period
    linestyles = (
        ["-"] * nb_color_period
        + ["--"] * nb_color_period
        + ["-."] * nb_color_period
        + [".."] * nb_color_period
    )

    if not isinstance(curves, Iterable):
        curves = [curves]
    abscissa_names = [curve.variable_names[0] for curve in curves]
    if abscissa_names.count(abscissa_names[0]) != len(abscissa_names):
        msg = f"Abscissa names are not unique: {abscissa_names}"
        raise ValueError(msg)

    file_name = "curves.html" if file_name == "" else file_name
    fig = Figure()
    i = -1
    for i, color, linestyle, curve in zip(
        range(4 * nb_color_period - 1), colors, linestyles, curves[:-1], strict=False
    ):
        curve.plot(
            save=save,
            show=show,
            fig=fig,
            color=color,
            linestyle=linestyle,
            label=labels[i] if len(labels) > 0 else "",
        )
    curves[-1].plot(
        directory_path=directory_path,
        save=save,
        show=show,
        file_name=file_name,
        fig=fig,
        color=colors[i + 1],
        linestyle=linestyles[i + 1],
        label=labels[i + 1] if len(labels) > 0 else "",
    )
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
