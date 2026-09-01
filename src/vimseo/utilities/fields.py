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
from dataclasses import field
from typing import TYPE_CHECKING

from meshio import CellBlock
from meshio import read

if TYPE_CHECKING:
    from pathlib import Path

    from meshio import Mesh
    from numpy import ndarray


@dataclass(eq=False)
class MeshField:
    """A field defined over a mesh.

    The field holds the mesh geometry together with the variables defined at its
    points and cells, as read by ``meshio``.
    """

    mesh_points: ndarray | None = None
    """The coordinates of the mesh points, of shape ``(n_points, 3)``."""

    mesh_cells: list[CellBlock] = field(default_factory=list)
    """The mesh cells, one block per cell type."""

    point_data: dict[str, ndarray] = field(default_factory=dict)
    """The variables defined at the mesh points."""

    cell_data: dict[str, list[ndarray]] = field(default_factory=dict)
    """The variables defined at the cells, one array per cell block."""

    path: str = ""
    """The path of the file the field was read from, empty if none."""

    name: str = ""
    """The name of the field, e.g. the zone name for a multi-zone mesh file."""

    def __post_init__(self) -> None:
        """Cast the path to a string, so that a ``Path`` is also accepted."""
        self.path = str(self.path)

    @property
    def cell_variable_names(self) -> list[str]:
        return list(self.cell_data.keys())

    @property
    def point_variable_names(self) -> list[str]:
        return list(self.point_data.keys())

    @classmethod
    def from_mesh(cls, mesh: Mesh, path: Path | str = "", name: str = "") -> MeshField:
        """Build a field from an already-read mesh.

        Args:
            path: The path the mesh was read from.
            mesh: The mesh to build the field from.
            name: The name of the field, e.g. the zone name for a multi-zone
                mesh file.

        Returns:
            The field.
        """
        return cls(
            path=path,
            name=name,
            point_data=mesh.point_data,
            cell_data=mesh.cell_data,
            mesh_points=mesh.points,
            mesh_cells=mesh.cells,
        )

    @classmethod
    def load(cls, path: Path | str) -> MeshField:
        """Load a field from a mesh file.

        Args:
            path: The path to the mesh file.

        Returns:
            The field.
        """
        return cls.from_mesh(read(path), path)
