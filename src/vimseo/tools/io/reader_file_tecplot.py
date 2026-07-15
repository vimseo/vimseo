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

from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from meshio import read
from pydantic import Field

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.io.base_reader_file import BaseReaderFile
from vimseo.tools.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.tools.io.field_result import FieldResult
from vimseo.utilities.fields import Field as MeshField

if TYPE_CHECKING:
    from collections.abc import Mapping

_FORMAT = "tecplot"


def _rename_header_variables(text: str, variable_name_aliases: Mapping[str, str]) -> str:
    """Rename the variables declared in a Tecplot ``VARIABLES`` header line.

    meshio only recognizes coordinate variables named ``X``/``Y``/``Z``, while some
    CFD tools export Tecplot files with other names (e.g. ``CoordinateX``). This
    renames the declared variables so that meshio's Tecplot reader can be reused as is.

    Args:
        text: The content of the Tecplot file.
        variable_name_aliases: The mapping from the variable names declared in the file
            to the names expected by meshio.

    Returns:
        The content of the Tecplot file with the ``VARIABLES`` header renamed.
    """
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("VARIABLES"):
            for source_name, target_name in variable_name_aliases.items():
                line = line.replace(f'"{source_name}"', f'"{target_name}"')
            lines[i] = line
            break
    return "".join(lines)


class ReaderFileTecplotSettings(BaseFileReaderSettings):
    """Settings of a Tecplot ASCII file reader."""

    variable_name_aliases: dict[str, str] = Field(
        default={},
        description="The mapping from the variable names declared in the file's "
        "VARIABLES header to the names expected by meshio's Tecplot reader "
        '(``"X"``, ``"Y"``, ``"Z"`` for the coordinates), '
        'e.g. ``{"CoordinateX": "X", "CoordinateY": "Y", "CoordinateZ": "Z"}``. '
        "Left empty when the file already uses these names.",
    )


class ReaderFileTecplot(BaseReaderFile):
    """Reads a Tecplot ASCII file into a mesh-based field."""

    results: FieldResult

    _EXTENSION = ".dat"

    _SETTINGS = ReaderFileTecplotSettings

    def __init__(
        self,
    ):
        super().__init__()
        self.result = FieldResult()

    @BaseTool.validate
    def execute(
        self,
        settings: ReaderFileTecplotSettings | None = None,
        **options,
    ) -> FieldResult:
        file_name = options["file_name"]
        directory_path = options["directory_path"]
        if Path(file_name).suffix != self._EXTENSION:
            msg = f"{self.__class__.__name__} requires the file suffix to be {self._EXTENSION}."
            raise ValueError(msg)
        file_path = (
            file_name if directory_path == "" else Path(directory_path) / file_name
        )

        variable_name_aliases = options["variable_name_aliases"]
        if variable_name_aliases:
            text = Path(file_path).read_text()
            text = _rename_header_variables(text, variable_name_aliases)
            mesh = read(StringIO(text), file_format=_FORMAT)
        else:
            mesh = read(file_path, file_format=_FORMAT)

        self.result.field = MeshField.from_mesh(file_path, mesh)
