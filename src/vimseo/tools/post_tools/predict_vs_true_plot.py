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

import numpy as np
import plotly.graph_objects as go
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import array
from numpy import sign

from vimseo.config.global_configuration import _configuration as config
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter
from vimseo.utilities.datasets import get_values

if TYPE_CHECKING:
    from pathlib import Path

    from pandas import DataFrame


class PredictVsTrue(Plotter):
    """A predict versus true plot."""

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )
        self.warning_msg = ""

    @BaseTool.validate
    def execute(
        self,
        df: DataFrame,
        metric_name: str,
        output_name: str,
        /,
        show: bool = False,
        save: bool = True,
        file_format: str = "html",
        hovering_variable_name: str | tuple[str] = "",
    ):
        """

        Args:
            df: TODO describe expected column naming

        """
        # TODO function to decapsulate tuple if needed
        if isinstance(hovering_variable_name, tuple):
            hovering_variable_name = hovering_variable_name[0]
            hovering_group_name = hovering_variable_name[1]
        else:
            hovering_group_name = metric_name
        hovering_variable_name = hovering_variable_name or output_name

        out_true = df[f"{output_name}[ReferenceOutputs]"].to_numpy()
        out_pred = df[f"{output_name}[{IODataset.OUTPUT_GROUP}]"].to_numpy()
        metrics = df[f"{output_name}[{metric_name}]"].to_numpy()

        marker_dict = {
            "color": metrics,
            "colorbar": {"title": metric_name},
            "colorscale": "rainbow",
            # cmid=0,
            "size": 8,
            "showscale": True,
            "line": {"width": 2, "color": "lightgrey"},
        }

        figure = go.Figure(
            data=go.Scatter(
                x=out_true,
                y=out_pred,
                mode="markers",
                marker=marker_dict,
                customdata=(
                    metrics
                    if hovering_variable_name == ""
                    else get_values(
                        df, hovering_variable_name, group_name=hovering_group_name
                    )
                ),
                hovertemplate="<b> Point prop<br>"
                "Ref: %{x}<br>"
                "Sim: %{y}<br>"
                f"{hovering_variable_name}[{hovering_group_name}]: %{{customdata: .2f}}",
                name="Simulated_vs_Reference",
                showlegend=False,
                # error_x=dict(
                #     type="data",
                #     array=[true_error_bar[i] for i in range(size(out_true))],
                #     thickness=1.0,
                # ),
                # error_y=dict(
                #     type="data",
                #     array=[pred_error_bar[i] for i in range(size(out_pred))],
                #     thickness=1.0,
                # ),
            )
        )
        extremum_out_true = sign(np.max(out_true)) * np.max(np.abs(out_true))
        for name, factor, line in [
            ("Identity line", 1.0, "dash"),
            ("-10% error", 0.9, "dot"),
            ("+10% error", 1.1, "dot"),
        ]:
            figure.add_scatter(
                x=array([0.0, extremum_out_true]),
                y=array([0.0, extremum_out_true * factor]),
                name=name,
                mode="lines",
                line={"color": "grey", "dash": line, "width": 2},
                showlegend=False,
            )

        figure.add_annotation(
            text="<b>+10%</b>",
            x=max(out_true * 1.02),
            y=max(out_true * 1.1),
            showarrow=False,
            font_size=14,
        )

        figure.add_annotation(
            text="<b>-10%</b>",
            x=max(out_true * 1.02),
            y=max(out_true * 0.9),
            showarrow=False,
            font_size=14,
        )

        figure.update_layout(
            title=f"<b>Simulation versus Reference - {output_name}</b>",
            xaxis_title=f"<b>Reference {output_name}",  # +/-std</b>",
            yaxis_title=f"<b>Simulated {output_name}",  # +/-std</b>",
            autosize=False,
            width=1200,
            height=800,
        )

        figure.update_layout(plot_bgcolor="white", font={"size": 20})
        figure.update_xaxes(
            mirror=True,
            ticks="outside",
            # showline=True,
            # linecolor="black",
            gridcolor="lightgrey",
            range=[0.0, None],
        )
        figure.update_yaxes(
            mirror=True,
            ticks="outside",
            showline=False,
            # linecolor="black",
            gridcolor="lightgrey",
            range=[0.0, None],
        )
        if self.options["save"]:
            figure.write_html(
                self.working_directory
                / f"metric_histogram_{metric_name}_{output_name}.html"
            )
        if self.options["show"]:
            figure.show()

        self.result.figure = figure
