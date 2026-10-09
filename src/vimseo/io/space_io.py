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

import json
import logging
from pathlib import Path
from typing import BinaryIO
from typing import TextIO

from gemseo.algos.parameter_space import ParameterSpace

from vimseo.io.base_tool_io import BaseToolFileIO
from vimseo.lib_vimseo.solver_utilities import EnhancedJSONEncoderModelWrapper
from vimseo.tools.space.random_variable_interface import add_distributions_from_dict
from vimseo.tools.space.random_variable_interface import distributions_to_dict
from vimseo.tools.space.space_tool_result import SpaceToolResult

LOGGER = logging.getLogger(__name__)


# TODO work at more atomic level, for exmaple metadata, parameter space, dataset
#  Then the load_result, save_result methods are in charge of calling these io to
#  create the final tool result.
class SpaceToolFileIO(BaseToolFileIO):
    _EXTENSION = ".json"

    def read(
        self, file_name: str | Path, directory_path: str | Path = ""
    ) -> SpaceToolResult:
        """Read a space tool result."""

        if Path(file_name).suffix != self._EXTENSION:
            msg = f"{self.__class__.__name__} requires the file suffix to be {self._EXTENSION}."
            raise ValueError(msg)
        file_path = (
            file_name if directory_path == "" else Path(directory_path) / file_name
        )
        with Path(file_path).open() as f:
            data = json.load(f)

        result = SpaceToolResult()
        result.parameter_space = ParameterSpace()
        result.metadata = self.create_metadata(data)
        result.parameter_space = self.create_parameter_space(data)
        return result

    def read_buffer(self, buf: BinaryIO | TextIO) -> SpaceToolResult:
        """Read a space tool result."""

        data = json.loads(buf)

        result = SpaceToolResult()
        result.parameter_space = ParameterSpace()
        result.metadata = self.create_metadata(data)
        result.parameter_space = self.create_parameter_space(data)
        return result

    @classmethod
    def create_parameter_space(cls, data):
        parameter_space = ParameterSpace()
        add_distributions_from_dict(parameter_space, data["parameter_space"])
        return parameter_space

    def write(
        self,
        result: SpaceToolResult,
        file_base_name: str | Path = "",
        directory_path: str | Path = "",
    ) -> dict:
        data = {
            "parameter_space": distributions_to_dict(result.parameter_space),
            "metadata": result.metadata,
        }
        json_data = json.dumps(
            data,
            ensure_ascii=True,
            indent=4,
            cls=EnhancedJSONEncoderModelWrapper,
        )

        if file_base_name == "":
            LOGGER.warning("No base file name provided, no file is written.")
            return json_data

        if file_base_name != "":
            directory_path = (
                Path.cwd() if directory_path == "" else Path(directory_path)
            )
            file_path = directory_path / f"{file_base_name}{self._EXTENSION}"
            Path(file_path).write_text(json_data)

        return json_data
