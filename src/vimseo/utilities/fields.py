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
    def load(cls, path: Path | str):
        field = read(path)
        return cls(
            path=path,
            point_data=field.point_data,
            cell_data=field.cell_data,
            mesh_points=field.points,
            mesh_cells=field.cells,
        )
