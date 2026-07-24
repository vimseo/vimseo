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
from pydantic import field_validator

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.io.base_reader_file import BaseReaderFile
from vimseo.tools.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.tools.io.field_result import FieldResult
from vimseo.utilities.fields import Field as MeshField

if TYPE_CHECKING:
    from collections.abc import Mapping

_FORMAT = "tecplot"


def _rename_header_variables(
    text: str,
    provided_coordinate_names: tuple[str, str, str],
    variable_name_aliases: Mapping[str, str],
    expected_coordinate_names: tuple[str, str, str] = ("X", "Y", "Z"),
) -> str:
    """Rename the variables declared in a Tecplot ``VARIABLES`` header line.

    meshio only recognizes coordinate variables named ``X``/``Y``/``Z``, while some
    CFD tools export Tecplot files with other names (e.g. ``CoordinateX``). This
    renames the declared variables so that meshio's Tecplot reader can be reused as is.

    This also renames the other variables according to user defined aliases, if any is
    provided.

    Args:
        text: The content of the Tecplot file.
        provided_coordinate_names: The names of the spatial coordinates as defined in
            the file header.
        variable_name_aliases: The mapping from the variable names declared in the file
            to the user defined aliases.
        expected_coordinate_names: The names of the spatial coordinate
            expected by meshio.

    Returns:
        The content of the Tecplot file with the ``VARIABLES`` header renamed.
    """
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("VARIABLES"):
            for i_coord in range(3):
                line = line.replace(
                    f'"{provided_coordinate_names[i_coord]}"',
                    f'"{expected_coordinate_names[i_coord]}"',
                )
            for source_name, target_name in variable_name_aliases.items():
                line = line.replace(f'"{source_name}"', f'"{target_name}"')
            lines[i] = line
            break
    return "".join(lines)


class ReaderFileTecplotSettings(BaseFileReaderSettings):
    """Settings of a Tecplot ASCII file reader."""

    coordinate_names: tuple[str, str, str] = Field(
        default=("X", "Y", "Z"),
        description="The names of the VARIABLES corresponding to spatial coordinates "
        "as defined in the header of the file.\n"
        'e.g. ``("CoordinateX", "CoordinateY", "CoordinateZ")``. ',
    )

    variable_name_aliases: dict[str, str] = Field(
        default={},
        description="User define aliases for the variables defined in the header."
        'In the form ``{"name in the file": "user defined alias"}``'
        'e.g. ``{"rho": "density", "mu": "dynamic viscosity"}``. '
        "DO NOT intend to rename the coordinate variables.",
    )

    @field_validator("variable_name_aliases", mode="after")
    @classmethod
    def remove_coordinate_aliases(cls, alias_dict: dict[str, str]) -> dict[str, str]:
        """Remove the coordinates from the alias dictionnary if present.

        Args:
            alias_dict (dict[str, str]): The dictionnary containing the aliases.

        Returns:
            dict[str, str]: The alias dictionnary minus the coordinate names.
        """
        for coord in ["X", "Y", "Z"]:
            alias_dict.pop(coord, None)
        return alias_dict


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

        coordinate_names = options["coordinate_names"]
        variable_name_aliases = options["variable_name_aliases"]
        if variable_name_aliases:
            text = Path(file_path).read_text()
            text = _rename_header_variables(
                text, coordinate_names, variable_name_aliases, ["X", "Y", "Z"]
            )
            mesh = read(StringIO(text), file_format=_FORMAT)
        else:
            mesh = read(file_path, file_format=_FORMAT)

        self.result.field = MeshField.from_mesh(file_path, mesh)
