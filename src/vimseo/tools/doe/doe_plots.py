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

"""The figures of the result of a DOE.

Besides a scatter matrix of the scalar variables, the result of a DOE varying a single
input, e.g. a mesh size study, is shown as a parametric study:

- the scalar outputs versus the varying input, in a grid of figures,
- the curves of each sample superposed, for each figure declared by the ``PLOTS`` of
  the model.
"""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

from numpy import argsort
from numpy import hstack
from numpy import unique

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence

    from matplotlib.figure import Figure as MatplotlibFigure
    from numpy import ndarray
    from plotly.graph_objs import Figure

    from vimseo.tools.post_tools.plot_parameters import Plot

N_COLUMNS = 4
"""The number of columns of the grid of the scalar outputs."""

COLOR_SCALE = "Blues"
"""The color scale identifying the samples, from the first one to the last one."""


def get_sample_colors(n_samples: int) -> list[str]:
    """Return a color per sample, from light to dark.

    Args:
        n_samples: The number of samples.
    """
    from plotly.colors import sample_colorscale

    if n_samples == 1:
        return sample_colorscale(COLOR_SCALE, [0.8])
    return sample_colorscale(
        COLOR_SCALE, [0.4 + 0.6 * i / (n_samples - 1) for i in range(n_samples)]
    )


def get_scalar_names(data: Mapping[str, ndarray], names: Iterable[str]) -> list[str]:
    """Return the names of the numerical scalar variables.

    The variables which are not numbers, e.g. the metadata of the model like the
    name of the user, are discarded.

    Args:
        data: The values of the variables, shaped as ``(n_samples, size)``.
        names: The names of the variables to filter.
    """
    return [
        name
        for name in names
        if name in data and data[name].shape[1] == 1 and data[name].dtype.kind in "biuf"
    ]


def get_varying_names(data: Mapping[str, ndarray], names: Iterable[str]) -> list[str]:
    """Return the names of the scalar variables varying from a sample to another.

    Args:
        data: The values of the variables, shaped as ``(n_samples, size)``.
        names: The names of the variables to filter.
    """
    return [
        name for name in get_scalar_names(data, names) if len(unique(data[name])) > 1
    ]


def create_scatter_matrix(
    data: Mapping[str, ndarray], variable_names: Sequence[str]
) -> MatplotlibFigure | None:
    """Create the scatter matrix of scalar variables.

    Args:
        data: The values of the variables, shaped as ``(n_samples, size)``.
        variable_names: The names of the scalar variables.

    Returns:
        The figure, or ``None`` if there are less than two variables.
    """
    if len(variable_names) < 2:
        return None

    from gemseo.datasets.dataset import Dataset
    from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix

    # A dataset holding only these variables, each once, whatever its group.
    dataset = Dataset.from_array(
        hstack([data[name] for name in variable_names]), variable_names=variable_names
    )
    return ScatterMatrix(dataset, kde=False).execute(save=False, show=False)[0]


def create_scalar_outputs_figure(
    data: Mapping[str, ndarray],
    abscissa_name: str,
    output_names: Sequence[str],
    title: str = "",
) -> Figure:
    """Create a grid of figures of the scalar outputs versus an input.

    Args:
        data: The values of the variables, shaped as ``(n_samples, size)``.
        abscissa_name: The name of the scalar input.
        output_names: The names of the scalar outputs.
        title: The title of the figure.

    Returns:
        The figure, with a subplot per output.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    abscissa = data[abscissa_name][:, 0]
    order = argsort(abscissa, kind="stable")
    colors = get_sample_colors(len(abscissa))
    n_columns = min(N_COLUMNS, len(output_names))
    n_rows = ceil(len(output_names) / n_columns)
    fig = make_subplots(
        rows=n_rows,
        cols=n_columns,
        subplot_titles=list(output_names),
        horizontal_spacing=0.08,
        vertical_spacing=0.25 / n_rows,
    )
    for index, name in enumerate(output_names):
        row, column = divmod(index, n_columns)
        fig.add_trace(
            go.Scatter(
                x=abscissa[order],
                y=data[name][order, 0],
                mode="lines+markers",
                line={"color": colors[len(colors) // 2]},
                marker={"color": [colors[i] for i in order], "size": 9},
                name=name,
                showlegend=False,
            ),
            row=row + 1,
            col=column + 1,
        )
        fig.update_xaxes(title_text=abscissa_name, row=row + 1, col=column + 1)
    fig.update_layout(title_text=title, height=300 * n_rows)
    return fig


def create_curve_figures(
    data: Mapping[str, ndarray],
    plots: Iterable[Plot],
    labels: Sequence[str],
) -> dict[str, Figure]:
    """Create the figures superposing the curves of the samples.

    A figure is created for each plot whose variables are all in the data,
    and at least one of them is a vector.

    Args:
        data: The values of the variables, shaped as ``(n_samples, size)``.
        plots: The definitions of the figures, typically the ``PLOTS`` of the model.
        labels: The label of each sample.

    Returns:
        The figures, whose keys are ``curves_{plot name}``.
    """
    from vimseo.utilities.curves import CurveSet
    from vimseo.utilities.plotting_utils import superpose_curves

    colors = get_sample_colors(len(labels))
    figures = {}
    for plot in plots:
        names = plot.variable_names
        if not all(name in data for name in names) or all(
            data[name].shape[1] == 1 for name in names
        ):
            continue

        curve_sets = [
            CurveSet.from_data(plot, {name: data[name][i] for name in names})
            for i in range(len(labels))
        ]
        fig = superpose_curves(curve_sets, labels=labels, show=False, save=False)
        if not plot.title:
            ordinate_names = ", ".join(trace.y for trace in plot.variable_traces)
            fig.update_layout(title_text=f"{ordinate_names} vs {plot.x}")
        if len(plot.traces) == 1:
            # A single line per sample: the color identifies the sample, from light
            # to dark, and the legend the value of the varying input.
            for line, color, label in zip(fig.data, colors, labels, strict=True):
                line.line.color = color
                line.marker.color = color
                line.name = label
        figures[f"curves_{plot.get_name()}"] = fig
    return figures
