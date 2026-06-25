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
from gemseo.datasets.io_dataset import IODataset
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix as GemseoScatterMatrix

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter
from vimseo.utilities.datasets import dataframe_to_dataset

if TYPE_CHECKING:
    from pandas import DataFrame

# from vimseo.utilities.datasets import dataframe_to_dataset


class ErrorScatterMatrix(Plotter):
    """A scatter matrix plot of an error metric."""

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
        ds = dataframe_to_dataset(df)

        # Create a dataset containing only the inputs and the specified metric:
        dataset = Dataset()
        for name in ds.get_variable_names(IODataset.INPUT_GROUP):
            dataset.add_variable(
                data=ds.get_view(
                    group_names=IODataset.INPUT_GROUP, variable_names=name
                ).to_numpy(),
                variable_name=name,
                group_name=IODataset.INPUT_GROUP,
            )
        dataset.add_variable(
            data=ds.get_view(
                group_names=metric_name, variable_names=output_name
            ).to_numpy(),
            variable_name=output_name,
            group_name=metric_name,
        )
        dataset.rename_variable(
            output_name, f"{metric_name}[{output_name}]", group_name=metric_name
        )

        scatter_matrix = GemseoScatterMatrix(
            dataset,
            kde=True,
            coloring_variable=f"{metric_name}[{output_name}]",
            axis_labels_as_keys=True,
            dimensions=ds.get_variable_names(IODataset.INPUT_GROUP),
        )
        scatter_matrix.title = f"Metric {metric_name} for output {output_name}"
        self.result.figure = scatter_matrix.execute(
            save=save,
            show=show,
            file_format="html",
            directory_path=self.working_directory,
            file_name=f"error_scatter_matrix_{metric_name}_{output_name}",
        )[0]
