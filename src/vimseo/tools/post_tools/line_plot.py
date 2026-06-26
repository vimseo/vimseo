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

from gemseo.post.dataset.lines import Lines as GemseoLines

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from gemseo.datasets.io_dataset import IODataset


# TODO Pass **options to DatasetPlot constructor.
class Lines(Plotter):
    """A generic line plot."""

    @BaseTool.validate
    def execute(
        self,
        dataset: IODataset,
        variables: Sequence[str],
        abscissa_variable: str,
        /,
        show: bool = False,
        save: bool = True,
        file_format: str = "html",
        file_name: str = "",
    ):
        dataset = dataset.sort_values([
            (dataset.get_group_names(abscissa_variable)[0], abscissa_variable, 0)
        ])
        line_plot = GemseoLines(
            dataset,
            abscissa_variable=abscissa_variable,
            variables=variables,
        )
        self.result.figure = line_plot.execute(
            file_format=file_format,
            save=save,
            show=show,
            directory_path=self.working_directory,
            file_name=(
                f"lines_outputs_{variables}_versus_{abscissa_variable}"
                if file_name == ""
                else file_name
            ),
        )
