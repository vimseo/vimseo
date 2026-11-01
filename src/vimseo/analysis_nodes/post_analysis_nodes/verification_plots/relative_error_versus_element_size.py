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
from plotly.graph_objs import Figure

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.post_analysis_nodes.base_plot import Plotter

if TYPE_CHECKING:
    from vimseo.analysis_nodes.verification.verification_result import (
        SolutionVerificationResult,
    )


class RelativeErrorVersusElementSizePlotter(Plotter):
    r"""A line plot showing the element size versus the relative error
    :math:`\frac{q - q_{extrap}}{q_{extrap}}`."""

    @BaseAnalysisNode._validate
    def execute(
        self,
        result: SolutionVerificationResult,
        /,
        show: bool = False,
        save: bool = True,
    ):
        df = result.simulation_and_reference.copy()
        df.columns = result.simulation_and_reference.get_columns()
        output_name = result.metadata.settings["output_name"]
        # Use the selected converged value (Richardson, or a palliative when
        # Richardson is nan) so the relative error stays finite and plottable.
        q_converged = result.extrapolation.get(
            "q_converged", result.extrapolation["q_extrap"]
        )
        df["relative_error"] = (df[output_name] - q_converged) / q_converged
        element_size_variable_name = result.metadata.misc["element_size_variable_name"]

        fig = Figure()
        fig.add_traces(
            go.Scatter(
                x=df[element_size_variable_name],
                y=df["relative_error"],
                name=f"{output_name}",
                mode="lines+markers",
                marker_color="blue",
            )
        )
        fig.update_yaxes(
            title=f"Relative error on {output_name}",
            minor={"ticks": "inside", "ticklen": 6, "showgrid": True},
        )
        fig.update_xaxes(
            title=f"{element_size_variable_name}",
            minor={"ticks": "inside", "ticklen": 6, "showgrid": True},
        )
        # TODO commonalize in Plotter
        if save:
            fig.write_html(
                self.working_directory / f"{output_name}_error_versus_element_size.html"
            )
        if show:
            fig.show()
        self.result.figure = fig
        return fig
