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

from pathlib import Path
from typing import TYPE_CHECKING

import plotly.express as px

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter

if TYPE_CHECKING:
    from pandas import DataFrame


class ParallelCoordinates(Plotter):
    """A Parallel coordinates plot of the error metrics."""

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
        **options,
    ):
        """
        Args:
            threshold: The threshold used a mid-point for the parallel coordinates plot
            color bar.

        """
        self.result.figure = px.parallel_coordinates(
            data_frame=df,
            color=output_name,
            dimensions=df.columns,
            color_continuous_scale=px.colors.sequential.Rainbow,
            color_continuous_midpoint=self.options["threshold"],
        )
        self.result.figure.layout.margin.t = 150
        self.result.figure.layout.title.text = (
            f"Metric {metric_name} for output {output_name}"
        )
        self.result.figure.layout.title.x = 0.5
        self.result.figure.update_layout(font_size=14)

        if self.options["show"]:
            self.result.figure.show()
        if self.options["save"]:
            self.result.figure.write_html(
                Path(self.working_directory)
                / f"parallel_coordinates_{metric_name}_{output_name}.html"
            )
