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
from typing import TYPE_CHECKING
from typing import ClassVar

from meshio import Mesh
from numpy import arctan2
from numpy import array
from numpy import atleast_1d
from numpy import column_stack
from numpy import linspace
from numpy import meshgrid
from numpy import nan
from numpy import sqrt
from numpy import zeros

from vimseo.core.base_component import BaseComponent
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.lib_vimseo.tan_lib import tan_model

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

LOGGER = logging.getLogger(__name__)

DEFAULT_INPUT_DATA = {
    "d0": atleast_1d(0.71),
    "radius": atleast_1d(3.175),
    "width": atleast_1d(32.0),
    "length": atleast_1d(50.0),
    "load": array([5000, 0, 0]),
    "n_x": atleast_1d(100),
    "n_y": atleast_1d(100),
    "c_strat": array([
        [453798.95833606, 80454.21661519, 0.0],
        [80454.21661519, 183534.41794582, 0.0],
        [0.0, 0.0, 86824.15717525],
    ]),
}


class TanRun_OHT(BaseComponent):
    """An Open Hole compression model based on Tan theory."""

    USE_JOB_DIRECTORY = True

    auto_detect_grammar_files = False
    default_grammar_type = "SimpleGrammar"

    def __init__(self, **options):
        super().__init__(**options)

        self.input_grammar.update_from_data(DEFAULT_INPUT_DATA)
        self.default_input_data.update(DEFAULT_INPUT_DATA)
        self.output_grammar.update_from_data({
            MetaDataNames.error_code.name: atleast_1d(0),
        })

    def _run(self, input_data):

        length = input_data["length"][0]
        width = input_data["width"][0]
        d0 = input_data["d0"][0]
        radius = input_data["radius"][0]
        n_x = input_data["n_x"][0]
        n_y = input_data["n_y"][0]

        load = input_data["load"]

        c_strat = input_data["c_strat"]

        output_data = {}

        x = linspace(0, length, n_x)
        y = linspace(0, width, n_y)

        # Create 2D grid coordinates
        xx, yy = meshgrid(x, y, indexing="ij")  # shape (nx, ny)

        # Flatten coordinates -> points array (nx*ny, 3)
        points = column_stack([
            xx.ravel(),
            yy.ravel(),
            zeros(n_x * n_y),  # z=0 for 2D
        ])

        # Create quad connectivity
        # Node index at (i,j) = i * ny + j
        quads = []
        for i in range(n_x - 1):
            for j in range(n_y - 1):
                n0 = i * n_y + j
                n1 = (i + 1) * n_y + j
                n2 = (i + 1) * n_y + (j + 1)
                n3 = i * n_y + (j + 1)
                quads.append([n0, n1, n2, n3])
        quads = array(quads)

        flux_n = zeros((n_x, n_y, 3))

        for i in range(n_x):
            for j in range(n_y):
                x_0 = x[i] - 0.5 * length
                y_0 = y[j] - 0.5 * width

                r = sqrt(x_0**2 + y_0**2)

                theta = arctan2(y_0, x_0)

                if r < radius + d0:
                    for k in range(3):
                        flux_n[i, j, k] = nan

                else:
                    res = tan_model(r, theta, load, c_strat, radius, width)

                    for k in range(3):
                        flux_n[i, j, k] = res[k]

        flatten_flux = flux_n.reshape(-1, 3)  # shape (nx*ny, 3)

        flux_field = Mesh(
            points=points,
            cells=[("quad", quads)],
            point_data={
                "N_xx": flatten_flux[:, 0],
                "N_yy": flatten_flux[:, 1],
                "N_xy": flatten_flux[:, 2],
            },
        )
        flux_field.write(self.job_directory / "flux.vtk")

        output_data[MetaDataNames.error_code] = atleast_1d(0.0)

        return output_data


class TanOpenHole(IntegratedModel):
    """An Open Hole model based on Tan theory."""

    CURVES: ClassVar[Sequence[tuple[str]]] = []

    FIELDS_FROM_FILE: ClassVar[Mapping[str, str]] = {"flux": r"^flux.vtk$"}

    def __init__(self, load_case_name: str, **options):
        options = IntegratedModelSettings(**options).model_dump()
        super().__init__(
            load_case_name,
            [
                ComponentFactory().create(
                    "TanRun",
                    load_case_name,
                )
            ],
            **options,
        )
