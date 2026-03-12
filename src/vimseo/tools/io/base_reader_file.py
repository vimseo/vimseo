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

from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool


class BaseReaderFileSettings(BaseSettings):
    file_name: str | Path = ""
    directory_path: str | Path = ""
    tool_name: str = ""


class StreamlitBaseReaderFileSettings(BaseSettings):
    """Streamlit settings for a base file reader."""


class BaseReaderFile(BaseTool):
    """A tool to read data."""

    _EXTENSION = ""

    def __init__(
        self,
    ):
        super().__init__(
            working_directory=Path.cwd(),
        )

    def get_file_extension(self):
        """The extension of the file containing the data."""
        return self._EXTENSION

    def _validate_base_options(self):
        file_name = self.options["file_name"]
        self.options["directory_path"] = Path(self.options["directory_path"])
        if Path(file_name).suffix != self._EXTENSION:
            msg = f"{self.__class__.__name__} requires the file suffix to be {self._EXTENSION}."
            raise ValueError(msg)
