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

from vimseo.material.material import Material
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.io.base_reader_file import BaseReaderFile
from vimseo.tools.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.tools.io.material_result import MaterialResult


class MaterialReaderFileSettings(BaseFileReaderSettings):
    """The settings of a material reader."""


class MaterialReader(BaseReaderFile):
    results: MaterialResult

    _EXTENSION = ".json"

    _SETTINGS = MaterialReaderFileSettings

    def __init__(
        self,
    ):
        super().__init__()
        self.result = MaterialResult()

    @BaseTool.validate
    def execute(
        self,
        settings: MaterialReaderFileSettings | None = None,
        **options,
    ) -> MaterialResult:
        file_name = options["file_name"]
        directory_path = Path(options["directory_path"])
        if Path(file_name).suffix != self._EXTENSION:
            msg = f"{self.__class__.__name__} requires the file suffix to be {self._EXTENSION}."
            raise ValueError(msg)
        self.result.material = Material.from_json(
            file_name=file_name, dir_path=directory_path
        )
        self.result.parameter_space = self.result.material.to_parameter_space()
