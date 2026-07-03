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

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pyvista as pv
from meshio import read
from numpy import array
from numpy import linalg

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence

    from numpy import ndarray

LOGGER = logging.getLogger(__name__)


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


def extract_line(
    vtu_file: str | Path,
    point_a: tuple[float] = (),
    point_b: tuple[float] = (),
    n_points: int = 200,
    fields: list[str] | None = None,
) -> dict:
    """
    Extract values from a vtu file along a line defined by two points.

    Args:
        vtu_file: The path to a vtu file.
        point_a: The starting point of the extraction line.
        point_b: The ending point of the extraction line.
        n_points: The number of equidistant points along the extraction line.
        fields: The names of the variables to extract.

    Returns:
        A dictionary mapping variable names to arrays containing the extracted
        values. The following keys are always present:

        - ``coords``: coordinates of the line points.
        - ``dist``: distance of the line points to the line start.
    """
    mesh = pv.read(vtu_file)

    pa = (
        array(point_a, dtype=float) if point_a else mesh.bounds[::2]
    )  # Use x_min, y_min, z_min if not provided
    pb = (
        array(point_b, dtype=float) if point_b else mesh.bounds[1::2]
    )  # Use x_max, y_max, z_max if not provided

    line = mesh.sample_over_line(tuple(pa), tuple(pb), resolution=n_points)

    coords = line.points
    dist = linalg.norm(coords - pa, axis=1)

    available = list(line.point_data.keys())
    if fields is None:
        fields = available
    else:
        missing = [f for f in fields if f not in available]
        fields = [f for f in fields if f in available]
        if missing:
            LOGGER.warning(
                f"Variables are not found in {vtu_file} : {missing}. "
                f"Available fields are: {available}"
            )

    result = {
        "coords": coords,
        "dist": dist,
    }
    for field in fields:
        result[field] = line.point_data[field]

    return result


def vtu_to_png(
    files: Sequence[str],
    scalar_name: str,
    output_folder: str,
    clim: tuple[float, float] | None = None,
):
    """Convert a sequence of .vtu files to .png images using PyVista."""

    # TODO voir comment extraire une composante d'un champ vectoriel (ex: Velocity) pour faire une image de cette composante uniquement

    # --- Boucle de rendu ---
    plotter = pv.Plotter(off_screen=True)  # Fenêtre invisible

    for i, filepath in enumerate(files):
        mesh = pv.read(filepath)

        # On vide le plotter à chaque itération pour ne pas superposer
        plotter.clear()

        # Ajout du maillage avec configuration de la colorbar
        plotter.add_mesh(
            mesh, scalars=scalar_name, cmap="viridis", clim=clim, show_scalar_bar=True
        )

        # Optionnel : Ajouter un titre ou le nom du fichier sur l'image
        plotter.add_text(f"Step: {i}", font_size=10, color="black")

        # Ajuster la caméra (automatique au premier fichier, puis fixe)
        if i == 0:
            plotter.view_xy()

        # Sauvegarde
        filename = Path(filepath).name.replace(".vtu", f"_{scalar_name}.png")
        save_path = Path(output_folder) / filename
        plotter.screenshot(save_path)

        LOGGER.info(f"Saved image: {filename}")

    plotter.close()
