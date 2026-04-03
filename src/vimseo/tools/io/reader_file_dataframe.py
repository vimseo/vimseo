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

from pathlib import Path
from typing import Any

from gemseo.datasets.io_dataset import IODataset
from pydantic import Field

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.io.base_reader_file import BaseReaderFile
from vimseo.tools.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.tools.io.dataset_result import DatasetResult
from vimseo.utilities.datasets import SEP


class ReaderFileDataFrameSettings(BaseFileReaderSettings):
    variable_names: list[str] = Field(
        default=[], description="The names of the variables."
    )
    variable_names_to_n_components: dict[str, int] | None = Field(
        default=None, description="The number of components of the variables."
    )
    variable_names_to_group_names: dict[str, str] | None = Field(
        default=None, description="The groups of the variables."
    )


class StreamlitReaderFileDataFrameSettings(ReaderFileDataFrameSettings):
    variable_names_to_n_components: dict[str, int] = Field(
        default={}, description="The number of components of the variables."
    )
    variable_names_to_group_names: dict[str, str] = Field(
        default={}, description="The groups of the variables."
    )

    def model_post_init(self, __context: Any) -> None:
        if self.variable_names_to_n_components == {}:
            self.variable_names_to_n_components = None
        if self.variable_names_to_group_names == {}:
            self.variable_names_to_group_names = None


class ReaderFileDataFrame(BaseReaderFile):
    results: DatasetResult

    _EXTENSION = ".csv"

    _SETTINGS = ReaderFileDataFrameSettings

    _STREAMLIT_SETTINGS = StreamlitReaderFileDataFrameSettings

    def __init__(
        self,
    ):
        super().__init__()
        self.result = DatasetResult()

    @BaseTool.validate
    def execute(
        self,
        settings: ReaderFileDataFrameSettings | None = None,
        **options,
    ) -> DatasetResult:
        file_name = options["file_name"]
        directory_path = options["directory_path"]
        if Path(file_name).suffix != self._EXTENSION:
            msg = f"{self.__class__.__name__} requires the file suffix to be {self._EXTENSION}."
            raise ValueError(msg)
        file_path = (
            file_name if directory_path == "" else Path(directory_path) / file_name
        )
        self.result.dataset = IODataset().from_txt(
            file_path,
            variable_names=options["variable_names"],
            variable_names_to_group_names=options["variable_names_to_group_names"],
            variable_names_to_n_components=options["variable_names_to_n_components"],
            delimiter=SEP,
        )
