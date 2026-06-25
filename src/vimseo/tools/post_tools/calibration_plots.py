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
from numpy import linspace
from plotly.graph_objs import Figure

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pandas import DataFrame


class CalibrationCurves(Plotter):
    """A line plot showing the reference versus simulated curves for calibration".

    The simulated curves are shown before and after calibration.
    """

    @BaseTool.validate
    def execute(
        self,
        posterior_dataframes: list[Mapping[str:DataFrame]],
        prior_dataframes: list[Mapping[str:DataFrame]],
        reference_dataframes: list[Mapping[str:DataFrame]],
        abscissa_name: str,
        output_name: str,
        /,
        load_case: str = "",
        font_size: int = 12,
        show: bool = False,
        save: bool = True,
    ):
        nb_samples = len(posterior_dataframes)
        marker_size = 10
        symbols = ["circle", "square", "diamond", "cross", "x", "triangle-up"]
        fig = Figure()
        for i in range(nb_samples):
            fig.add_traces(
                go.Scatter(
                    x=(
                        posterior_dataframes[i][output_name][abscissa_name]
                        if abscissa_name != "dummy_"
                        else linspace(
                            0.0,
                            1.0,
                            len(posterior_dataframes[i][output_name][output_name]),
                        )
                    ),
                    y=posterior_dataframes[i][output_name][output_name],
                    name=f"posterior {i}",
                    showlegend=True,
                    mode="lines+markers",
                    line_color="green",
                    marker={
                        "symbol": symbols[i % len(symbols)],
                        "size": marker_size,
                    },
                )
            )
            fig.add_traces(
                go.Scatter(
                    x=(
                        prior_dataframes[i][output_name][abscissa_name]
                        if abscissa_name != "dummy_"
                        else linspace(
                            0.0, 1.0, len(prior_dataframes[i][output_name][output_name])
                        )
                    ),
                    y=prior_dataframes[i][output_name][output_name],
                    name=f"prior {i}",
                    showlegend=True,
                    mode="lines+markers",
                    line_color="chocolate",
                    line={"dash": "dot", "width": 2},
                    marker={"symbol": symbols[i % len(symbols)], "size": marker_size},
                )
            )
            fig.add_traces(
                go.Scatter(
                    x=(
                        reference_dataframes[i][output_name][abscissa_name]
                        if abscissa_name != "dummy_"
                        else linspace(
                            0.0,
                            1.0,
                            len(reference_dataframes[i][output_name][output_name]),
                        )
                    ),
                    y=reference_dataframes[i][output_name][output_name],
                    name=f"reference {i}",
                    showlegend=True,
                    mode="lines",
                    line={"dash": "dashdot", "width": 2},
                )
            )
        fig.update_layout(
            xaxis_title=abscissa_name,
            yaxis_title=output_name,
            font_size=font_size,
            title={
                "text": f"Simulated versus reference for load case {load_case}",
                "font": {"size": font_size * 1.2},
            },
        )

        if show:
            fig.show()
        if save:
            file_name = (
                f"simulated_versus_reference_{output_name}_vs_{abscissa_name}_"
                f"load_case_{load_case}.html"
            )
            file_name = file_name.replace(":", "-")
            fig.write_html(self.working_directory / file_name)

        self.result.figure = fig
