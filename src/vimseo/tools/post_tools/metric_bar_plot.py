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

from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.bars import BarPlot

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter

if TYPE_CHECKING:
    from collections.abc import Mapping


class IntegratedMetricBars(Plotter):
    """Bar plot of the integrated value of a metric of a :class:`.VerificationResult`."""

    @BaseTool.validate
    def execute(
        self,
        integrated_metrics: Mapping[str, Mapping[str, float]],
        metric_name: str = "",
        /,
        show: bool = False,
        save: bool = True,
        file_format: str = "html",
    ):
        """Plot the integrated value of a metric for all variables in the metric group.

        Args:
            metric_name: The name of the metric to plot.
        """
        metric_names = [metric_name] if metric_name != "" else integrated_metrics.keys()
        ds = Dataset()
        for metric_name in metric_names:
            for variable_name, metric_value in integrated_metrics[metric_name].items():
                ds.add_variable(
                    data=metric_value,
                    variable_name=variable_name,
                    group_name=metric_name,
                )

        bar_plot = BarPlot(ds)
        bar_plot.font_size = 20
        bar_plot.title = metric_name
        self.result.figure = bar_plot.execute(
            file_format=file_format,
            save=save,
            show=show,
            directory_path=self.working_directory,
            file_name="integrated_metric_bars",
        )[0]
