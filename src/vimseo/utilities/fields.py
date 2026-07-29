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

from dataclasses import dataclass
from typing import TYPE_CHECKING

from meshio import read

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from meshio import Mesh
    from numpy import ndarray


@dataclass
class Field:
    """A field."""

    path: str | Path = ""
    point_data: ndarray | None = None
    cell_data: ndarray | None = None
    mesh_points: ndarray | None = None
    mesh_cells: ndarray | None = None

    @property
    def cell_variable_names(self) -> Iterable[str]:
        return list(self.cell_data.keys())

    @property
    def point_variable_names(self) -> Iterable[str]:
        return list(self.point_data.keys())

    @classmethod
    def from_mesh(cls, mesh: Mesh, path: Path | str = "") -> Field:
        """Build a field from an already-read mesh.

        Args:
            path: The path the mesh was read from.
            mesh: The mesh to build the field from.

        Returns:
            The field.
        """
        return cls(
            path=path,
            point_data=mesh.point_data,
            cell_data=mesh.cell_data,
            mesh_points=mesh.points,
            mesh_cells=mesh.cells,
        )

    @classmethod
    def load(cls, path: Path | str) -> Field:
        """Load a field from a mesh file.

        Args:
            path: The path to the mesh file.

        Returns:
            The field.
        """
        return cls.from_mesh(read(path), path)
