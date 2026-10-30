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

import plotly.graph_objects as go
from numpy import full
from numpy import isnan
from plotly.graph_objs import Figure

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.post_analysis_nodes.base_plot import Plotter
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots._constants import (
    _DOF_ABSCISSA_NAME,
)

if TYPE_CHECKING:
    from vimseo.analysis_nodes.verification.verification_result import (
        SolutionVerificationResult,
    )


class ErrorVersusElementSizePlotter(Plotter):
    """A line plot showing the error between the output values and the Richardson
    extrapolation, versus the element size."""

    def __compute_reference_lines_offset(self, y_data, x_data, cv_order, nb_meshes):
        y_ref = y_data[nb_meshes - 1]
        return (
            y_ref / x_data[nb_meshes - 1] ** cv_order
            if not isnan(y_ref)
            else 1.0 / x_data[nb_meshes - 1] ** cv_order
        )

    @BaseAnalysisNode._validate
    def execute(
        self,
        result: SolutionVerificationResult,
        /,
        show: bool = False,
        save: bool = True,
    ):
        df = result.element_wise_metrics.copy()
        df.columns = result.element_wise_metrics.get_columns()
        nb_meshes = df.shape[0]
        df["median_absolute_deviation"] = full(
            (nb_meshes),
            result.extrapolation.get(
                "q_converged_cv_mad", result.extrapolation["q_extrap_mad"]
            ),
        )
        if result.metadata.misc["element_size_variable_name"] == "degrees_of_freedom":
            element_size_variable_name = _DOF_ABSCISSA_NAME
        else:
            element_size_variable_name = result.metadata.misc[
                "element_size_variable_name"
            ]
        output_name = result.metadata.settings["output_name"]

        fig = Figure()
        fig.add_traces(
            go.Scatter(
                x=df[element_size_variable_name],
                y=df[output_name],
                name=f"|{output_name}-extrap|",
                mode="markers",
                marker_color="blue",
            )
        )
        for cv_order, coef, color in zip(
            [1, 2],
            [
                self.__compute_reference_lines_offset(
                    df[output_name], df[element_size_variable_name], 1, nb_meshes
                ),
                self.__compute_reference_lines_offset(
                    df[output_name], df[element_size_variable_name], 2, nb_meshes
                ),
            ],
            ["green", "black"],
            strict=False,
        ):
            fig.add_traces(
                go.Scatter(
                    x=df[element_size_variable_name],
                    y=coef * df[element_size_variable_name] ** cv_order,
                    name=f"order {cv_order}",
                    mode="lines",
                    line_color=color,
                    line={"dash": "dash"},
                )
            )
        fig.update_xaxes(type="log", title=element_size_variable_name)
        fig.update_xaxes(minor={"ticks": "inside", "ticklen": 6, "showgrid": True})
        fig.update_yaxes(type="log")
        fig.update_yaxes(minor={"ticks": "inside", "ticklen": 6, "showgrid": True})
        if save:
            fig.write_html(
                self.working_directory / f"{output_name}_error_versus_h.html"
            )
        if show:
            fig.show()
        self.result.figure = fig
        return fig
