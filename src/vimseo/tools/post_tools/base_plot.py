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

from abc import abstractmethod
from typing import TYPE_CHECKING

from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.config.global_configuration import _configuration as config
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.plot_result import PlotResult

if TYPE_CHECKING:
    from pathlib import Path

    from gemseo.datasets.dataset import Dataset
    from pandas import DataFrame

    from vimseo.tools.base_result import BaseResult


class Plotter(BaseTool):
    """Plot a tool result."""

    results: PlotResult

    _HAS_OPTION_CHECK = False

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
        self.result = PlotResult()

    @abstractmethod
    def _run(
        self,
        input_data: BaseResult | Dataset | DataFrame,
        *args,
        show: bool = False,
        save: bool = True,
        file_format: str = "html",
        **options,
    ):
        """

        Args:
            input_data: The plotted data.
            show: Whether to show the figure.
            save: Whether to save the figure on disk.
            file_format: The output file format of the figure.
            **options: The options of the plot.

        """
