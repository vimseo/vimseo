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

import plotly.express as px
from gemseo.datasets.io_dataset import IODataset

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.post_analysis_nodes.base_plot import Plotter

if TYPE_CHECKING:
    from gemseo.datasets.dataset import Dataset


class ErrorMetricHistogramPlotter(Plotter):
    """An histogram plot where the abscissa is the error value and the ordinate the
    number of verification points corresponding to this error."""

    @BaseAnalysisNode._validate
    def execute(
        self,
        element_wise_metrics: Dataset,
        metric_name: str,
        output_name: str,
        /,
        renamer=None,
        show: bool = False,
        save: bool = True,
    ):
        # Rename element-wise metrics to ensure variable names are unique.
        dataset = element_wise_metrics.copy()
        df = dataset.get_view(group_names=[IODataset.INPUT_GROUP, metric_name]).copy()
        df.columns = df.get_columns(as_tuple=False)
        output_name = output_name if not renamer else renamer(output_name, metric_name)
        fig = px.histogram(df, x=output_name)
        if save:
            fig.write_html(
                self.working_directory
                / f"metric_histogram_{metric_name}_{output_name}.html"
            )
        if show:
            fig.show()
        self.result.figure = fig
