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

from gemseo.datasets.io_dataset import IODataset

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.io.base_reader_file import BaseReaderFile
from vimseo.tools.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.tools.io.base_reader_file_settings import StreamlitBaseFileReaderSettings
from vimseo.tools.io.dataset_result import DatasetResult
from vimseo.utilities.datasets import SEP


class ReaderFileGemseoDatasetSettings(BaseFileReaderSettings):
    """Settings of a GEMSEO Dataset file reader."""


class StreamlitReaderFileGemseoDatasetSettings(StreamlitBaseFileReaderSettings):
    """Settings of a GEMSEO Dataset file reader for usage in dashboards."""


class ReaderFileGemseoDataset(BaseReaderFile):
    """Reads a GEMSEO dataset."""

    results: IODataset

    _EXTENSION = ".csv"

    _SETTINGS = ReaderFileGemseoDatasetSettings

    _STREAMLIT_SETTINGS = StreamlitReaderFileGemseoDatasetSettings

    def __init__(
        self,
    ):
        super().__init__()
        self.result = DatasetResult()

    def get_file_extension(self):
        return self._EXTENSION

    @BaseTool.validate
    def execute(
        self,
        settings: ReaderFileGemseoDatasetSettings | None = None,
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
        self.result.dataset = IODataset().from_csv(
            file_path,
            delimiter=SEP,
            first_column_as_index=True,
        )
