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

import plotly.graph_objects as go
from numpy import array

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter

if TYPE_CHECKING:
    from pandas import DataFrame

colormap = [
    "rgb(230, 240, 240)",
    "rgb(191, 221, 229)",
    "rgb(156, 201, 226)",
    "rgb(129, 180, 227)",
    "rgb(115, 154, 228)",
    "rgb(117, 127, 221)",
    "rgb(120, 100, 202)",
    "rgb(119, 74, 175)",
    "rgb(113, 50, 141)",
    "rgb(100, 31, 104)",
    "rgb(80, 20, 66)",
    "rgb(54, 14, 36)",
]
MARKERSIZE = 15


def compute_nb_trajectories(nb_data, nb_meshes):
    nb_trajectories = nb_data / nb_meshes
    if not nb_trajectories.is_integer():
        msg = (
            f"The length of convergence data should be a multiple of "
            f"the number of mesh refinements. But the length is "
            f"{nb_data} and the number of mesh "
            f"refinements is {nb_meshes}."
        )
        raise ValueError(msg)
    return int(nb_trajectories)


class ConvergenceCase(Plotter):
    """A comparison of several convergence trajectories."""

    @BaseTool.validate
    def execute(
        self,
        convergence_data: DataFrame,
        nb_meshes: int,
        elt_size_var_name: str,
        output_name: str,
        /,
        normalize_index_output: int | None = None,
        hovering_variables: list[str] = (),
        dark_mode: bool = False,
        show: bool = False,
        save: bool = True,
    ):
        fig = go.Figure()

        prefix = "" if normalize_index_output is None else "Normalized "

        nb_trajectories = compute_nb_trajectories(len(convergence_data), nb_meshes)

        for i in range(nb_trajectories):
            color = colormap[i * int((len(colormap) - 1) / (nb_trajectories - 1))]
            df_ = convergence_data.iloc[[j + i * nb_meshes for j in range(nb_meshes)]]
            y_values = (
                df_[output_name].values
                if normalize_index_output is None
                else df_[output_name].values
                / df_[output_name].values[normalize_index_output]
            )
            for j in range(len(df_)):
                if j < len(df_) - 1:
                    fig1 = go.Scatter(
                        x=[
                            df_[elt_size_var_name].values[j],
                            df_[elt_size_var_name].values[j + 1],
                        ],
                        y=[y_values[j], y_values[j + 1]],
                        line={"dash": "dash"},
                        name=i,
                        line_color=color,
                        showlegend=False,
                    )
                    fig.add_traces(fig1)
                fig2 = go.Scatter(
                    x=[df_[elt_size_var_name].values[j]],
                    y=[y_values[j]],
                    name=i,
                    line_color=color,
                    mode="markers",
                    marker_size=MARKERSIZE,
                    marker={"line": {"width": 2, "color": "lightgrey"}},
                    hovertemplate=", ".join([
                        f"{name}: {df_[name].values[j]}" for name in hovering_variables
                    ]),
                    showlegend=False,
                )
                fig.add_traces(fig2)

            y_values = array([
                df_[f"Ref[{output_name}]"].values[0],
                df_[output_name].values[-1],
            ])
            if normalize_index_output:
                y_values /= df_[output_name].values[normalize_index_output]
            fig2 = go.Scatter(
                x=[0.0, df_[elt_size_var_name].values[-1]],
                y=y_values,
                mode="lines",
                line={"dash": "dash", "color": color},
                name=i,
                showlegend=False,
            )
            fig.add_traces(fig2)

            for j in range(len(df_)):
                y_values = array([
                    df_["extrapolated_values_folds"].values[j],
                    df_[output_name].values[-1],
                ])
                if normalize_index_output:
                    y_values /= df_[output_name].values[normalize_index_output]
                fig3 = go.Scatter(
                    x=[0.0, df_[elt_size_var_name].values[-1]],
                    y=y_values,
                    mode="lines",
                    line={"dash": "dot", "color": color},
                    name=i,
                    showlegend=False,
                )
                fig.add_traces(fig3)

        fig.update_layout(
            height=700,
            xaxis_title=f"<b>{elt_size_var_name}</b>",
            xaxis_range=[0.0, None],
            margin={"l": 150, "b": 100},
            yaxis_title=f"<b>{prefix}{output_name}</b>",
        )
        fig.update_xaxes(
            title_font={"size": 40},
            tickfont={"size": 40},
            tickfont_family="Arial Black",
        )
        fig.update_yaxes(
            title_font={"size": 40},
            tickfont={"size": 40},
            tickfont_family="Arial Black",
        )
        if dark_mode:
            fig.layout.template = "plotly_dark"

        if save:
            fig.write_html(
                self.working_directory
                / f"convergence_case_{elt_size_var_name}_{output_name}.html"
            )
        if show:
            fig.show()
        self.result.figure = fig


class CpuTimeCompromiseCase(Plotter):
    @BaseTool.validate
    def execute(
        self,
        convergence_data: DataFrame,
        nb_meshes: int,
        elt_size_var_name: str,
        output_name: str,
        /,
        normalize_index_output: int | None = None,
        hovering_variables: list[str] = (),
        dark_mode: bool = False,
        show: bool = False,
        save: bool = True,
    ):

        fig = go.Figure()

        nb_trajectories = compute_nb_trajectories(len(convergence_data), nb_meshes)

        prefix = "" if normalize_index_output is None else "Normalized "
        hovering_variables += [elt_size_var_name]

        for i in range(nb_trajectories):
            color = colormap[i * int((len(colormap) - 1) / (nb_trajectories - 1))]
            df_ = convergence_data.iloc[[j + i * nb_meshes for j in range(nb_meshes)]]
            y_values = (
                df_[output_name].values
                if normalize_index_output is None
                else df_[output_name].values
                / df_[output_name].values[normalize_index_output]
            )
            if len(df_) > 0:
                for j in range(len(df_)):
                    if j < len(df_) - 1:
                        fig2 = go.Scatter(
                            x=[
                                df_["cpu_time"].values[j],
                                df_["cpu_time"].values[j + 1],
                            ],
                            y=[y_values[j], y_values[j + 1]],
                            line={"dash": "dash"},
                            line_color=color,
                            showlegend=False,
                        )
                        fig.add_traces(fig2)
                    fig1 = go.Scatter(
                        x=[df_["cpu_time"].values[j]],
                        y=[y_values[j]],
                        line_color=color,
                        mode="markers",
                        marker_size=MARKERSIZE,
                        marker={"line": {"width": 2, "color": "lightgrey"}},
                        hovertemplate=", ".join([
                            f"{name}: {df_[name].values[j]}"
                            for name in hovering_variables
                        ]),
                        showlegend=False,
                    )
                    fig.add_traces(fig1)

        fig.update_layout(
            height=700,
            xaxis_title="<b>CPU time(s)</b>",
            margin={"l": 150, "b": 100},
            yaxis_title=f"<b>{prefix}{output_name}</b>",
        )
        fig.update_xaxes(
            title_font={"size": 40},
            tickfont={"size": 40},
            tickfont_family="Arial Black",
        )
        fig.update_yaxes(
            title_font={"size": 40},
            tickfont={"size": 40},
            tickfont_family="Arial Black",
        )
        if dark_mode:
            fig.layout.template = "plotly_dark"
        if save:
            fig.write_html(
                self.working_directory / f"cpu_time_compromise_{output_name}.html"
            )
        if show:
            fig.show()
        return fig
