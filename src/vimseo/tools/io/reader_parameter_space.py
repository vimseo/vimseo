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

from vimseo.io.space_io import SpaceToolFileIO
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.io.base_reader_file import BaseReaderFile
from vimseo.tools.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.tools.space.space_tool_result import SpaceToolResult


class ParameterSpaceReaderFileSettings(BaseFileReaderSettings):
    """The settings of a parameter space reader."""


class ParameterSpaceReader(BaseReaderFile):
    results: SpaceToolResult

    _EXTENSION = ".json"

    _SETTINGS = ParameterSpaceReaderFileSettings

    def __init__(
        self,
    ):
        super().__init__()
        self.result = SpaceToolResult()

    @BaseTool.validate
    def execute(
        self,
        settings: ParameterSpaceReaderFileSettings | None = None,
        **options,
    ) -> SpaceToolResult:
        self._validate_base_options()
        self.result.parameter_space = (
            SpaceToolFileIO()
            .read(
                directory_path=options["directory_path"], file_name=options["file_name"]
            )
            .parameter_space
        )
