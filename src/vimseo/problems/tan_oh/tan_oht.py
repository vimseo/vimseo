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

from composipy import LaminateProperty
from meshio import Mesh
from numpy import arctan2
from numpy import array
from numpy import atleast_1d
from numpy import column_stack
from numpy import isnan
from numpy import linspace
from numpy import meshgrid
from numpy import nan
from numpy import sqrt
from numpy import zeros
from plotly.graph_objs import Scatter
from scipy.interpolate import interp1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.lib_vimseo.tan_lib import tan_model
from vimseo.material_lib.orthotropic import ORTHOTROPIC_MATERIAL
from vimseo.utilities.fields import extract_line
from vimseo.utilities.plotting_utils import plotly_save_and_show

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from pathlib import Path

    from vimseo.core.load_case import LoadCase
    from vimseo.material.material import Material

LOGGER = logging.getLogger(__name__)

NOMINAL_GRID_SIZE = 100

DEFAULT_INPUT_DATA = {
    "d0": atleast_1d(0.71),
    "radius": atleast_1d(3.175),
    "width": atleast_1d(32.0),
    "length": atleast_1d(50.0),
    "load": array([5000]),
    "coarsening_factor": atleast_1d(1.0),
    "stacking_sequence": array([0, 45, -45, 90, 90, -45, 45, 0]),
}

material = ORTHOTROPIC_MATERIAL
PLY_THICKNESS = 0.125e-3
material.update_from_dict(
    {
        "E1": 135e9,
        "E2": 10e9,
        "G12": 5e9,
        "nu12": 0.3,
        "Xt": 1500e6,
        "Xc": 1200e6,
        "Yt": 40e6,
        "Yc": 120e6,
        "S12": 50e6,
    },
    relation_name="orthotropic",
)
material.name_to_material_relation["orthotropic"].set_thickness(PLY_THICKNESS)
laminate = LaminateProperty(
    DEFAULT_INPUT_DATA["stacking_sequence"],
    material.name_to_material_relation["orthotropic"].get_relation(),
)
A = laminate.A  # Rigidité de membrane
# B = laminate.B  # Couplage (devrait être proche de 0 si symétrique)
# D = laminate.D  # Rigidité de flexion
total_thickness = len(DEFAULT_INPUT_DATA["stacking_sequence"]) * PLY_THICKNESS
c_eff = A / total_thickness

DEFAULT_INPUT_DATA["c_strat"] = c_eff
DEFAULT_INPUT_DATA["thickness"] = atleast_1d(total_thickness)


class TanRun_OHT(BaseComponent):
    """An Open Hole Tension model based on Tan theory (#open-hole-plate-model-tan-model)."""

    USE_JOB_DIRECTORY = True

    auto_detect_grammar_files = False
    default_grammar_type = "SimpleGrammar"

    def __init__(self, **options):
        super().__init__(**options)

        self.input_grammar.update_from_data(DEFAULT_INPUT_DATA)
        self.default_input_data.update(DEFAULT_INPUT_DATA)
        self.output_grammar.update_from_data({
            MetaDataNames.error_code.name: atleast_1d(0),
            "dx": atleast_1d(0.0),
            "dy": atleast_1d(0.0),
        })

    def _run(self, input_data):

        length = input_data["length"][0]
        width = input_data["width"][0]
        thickness = input_data["thickness"][0]
        input_data["d0"][0]
        radius = input_data["radius"][0]
        coarsening_factor = input_data["coarsening_factor"][0]
        n_x = int(NOMINAL_GRID_SIZE / coarsening_factor)
        n_y = int(NOMINAL_GRID_SIZE / coarsening_factor)
        dx = length / (n_x - 1)
        dy = width / (n_y - 1)

        load = array([input_data["load"][0], 0.0, 0.0]) / thickness

        c_strat = input_data["c_strat"]

        output_data = {}

        x_start = 0.0
        x_end = length
        y_start = 0.0
        y_end = width
        x = linspace(x_start, x_end, n_x)
        y = linspace(y_start, y_end, n_y)

        # Create 2D grid coordinates
        xx, yy = meshgrid(x, y, indexing="ij")  # shape (nx, ny)

        # Flatten coordinates -> points array (nx*ny, 3)
        points = column_stack([
            xx.ravel(),
            yy.ravel(),
            zeros(n_x * n_y),  # z=0 for 2D
        ])

        d0_ = 0.0
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

                if r < radius + d0_:
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
                "sigma_xx": flatten_flux[:, 0] * thickness,
                "sigma_yy": flatten_flux[:, 1] * thickness,
                "sigma_xy": flatten_flux[:, 2] * thickness,
            },
        )
        flux_field.write(self.job_directory / "flux.vtk")

        output_data[MetaDataNames.error_code] = atleast_1d(0)
        output_data["dx"] = atleast_1d(dx)
        output_data["dy"] = atleast_1d(dy)

        return output_data


class PostFieldExtraction(BaseComponent):
    """A post-processor to extract data from a field."""

    auto_detect_grammar_files = False
    default_grammar_type = "SimpleGrammar"

    def __init__(
        self,
        load_case: LoadCase | None = None,
        material_grammar_file: Path | str = "",
        material: Material | None = None,
        check_subprocess: bool = False,
        fields_from_file: Mapping[str, str] | None = None,
    ):
        super().__init__(
            load_case=load_case,
            material_grammar_file=material_grammar_file,
            material=material,
            check_subprocess=check_subprocess,
        )
        self._fields_from_file = fields_from_file

        input_names = ["length", "width", "radius", "d0", "dx", "dy"]

        self.input_grammar.update_from_data({
            name: array([0.0]) for name in input_names
        })

        for name in input_names:
            self.input_grammar.required_names.add(name)

        self._flux_components = ["sigma_xx", "sigma_yy", "sigma_xy", "Distance"]
        self._line_name = "line_center"
        for name in ["y", *self._flux_components]:
            self.output_grammar.update_from_names([f"{self._line_name}_{name}"])

        self.output_grammar.update_from_names(["sigma_xx_r", "sigma_xx_d0"])

    def _run(self, input_data):
        length = input_data["length"][0]
        width = input_data["width"][0]
        radius = input_data["radius"][0]
        d0 = input_data["d0"][0]
        input_data["dx"][0]
        input_data["dy"][0]

        line_extremities = {
            self._line_name: ((0.5 * length, 0.0, 0.0), (0.5 * length, width, 0.0)),
        }

        output_data = {}
        for line_name, extremities in line_extremities.items():
            line = extract_line(
                vtu_file=self.job_directory / "flux.vtk",
                point_a=extremities[0],
                point_b=extremities[1],
                n_points=100,
                fields=self._flux_components,
            )
            y = line["coords"][:, 1]
            output_data[f"{line_name}_y"] = y
            for name in self._flux_components:
                output_data[f"{line_name}_{name}"] = line[name]

        f = interp1d(
            y[~isnan(line["sigma_xx"])],
            line["sigma_xx"][~isnan(line["sigma_xx"])],
            bounds_error=False,
            fill_value="extrapolate",
            kind="quadratic",
        )
        output_data["sigma_xx_r"] = atleast_1d(f(0.5 * width + radius))
        output_data["sigma_xx_d0"] = atleast_1d(f(0.5 * width + radius + d0))

        # TODO: compute reserve factor based on strength criteria instead of just returning 1.0
        output_data["reserve_factor"] = atleast_1d(1.0)

        return output_data


class TanOpenHole(IntegratedModel):
    """An Open Hole model based on Tan theory."""

    CURVES: ClassVar[Sequence[tuple[str]]] = [("line_center_y", "line_center_sigma_xx")]

    FIELDS_FROM_FILE: ClassVar[Mapping[str, str]] = {"flux": r"^flux.vtk$"}

    def __init__(self, load_case_name: str, **options):
        options = IntegratedModelSettings(**options).model_dump()
        super().__init__(
            load_case_name,
            [
                ComponentFactory().create(
                    "TanRun",
                    load_case=LoadCaseFactory().create(load_case_name),
                ),
                PostFieldExtraction(
                    load_case=LoadCaseFactory().create(load_case_name),
                    fields_from_file=self.FIELDS_FROM_FILE,
                ),
            ],
            **options,
        )

    def _plot_curves(self, figures, result, directory_path, save, show):
        figures = super()._plot_curves(
            figures, result, directory_path, save=False, show=False
        )
        fig = figures["line_center_sigma_xx_vs_line_center_y"]

        width = self.get_input_data()["width"][0]
        radius = self.get_input_data()["radius"][0]
        d0 = self.get_input_data()["d0"][0]
        sigma_xx = self.get_output_data()["line_center_sigma_xx"]
        load_x = self.get_input_data()["load"][0]
        max_sigma = max(
            self.get_output_data()["sigma_xx_r"][0],
            self.get_output_data()["sigma_xx_d0"][0],
        )
        for y_radius in [0.5 * width - radius, 0.5 * width + radius]:
            fig.add_trace(
                Scatter(
                    x=[y_radius, y_radius],
                    y=[min(sigma_xx), max_sigma],
                    mode="lines",
                    line={"color": "green", "width": 2, "dash": "dash"},
                    name="radius",
                )
            )
            fig.add_trace(
                Scatter(
                    x=[y_radius],
                    y=[self.get_output_data()["sigma_xx_r"][0]],
                    mode="markers",
                    line={"color": "green", "width": 2, "dash": "dash"},
                    name="sigma_xx radius",
                )
            )
        for y_d0 in [0.5 * width - radius - d0, 0.5 * width + radius + d0]:
            fig.add_trace(
                Scatter(
                    x=[y_d0, y_d0],
                    y=[min(sigma_xx), max_sigma],
                    mode="lines",
                    line={"color": "red", "width": 2, "dash": "dash"},
                    name="radius+d0",
                )
            )
            fig.add_trace(
                Scatter(
                    x=[y_d0],
                    y=[self.get_output_data()["sigma_xx_d0"][0]],
                    mode="markers",
                    line={"color": "red", "width": 2, "dash": "dash"},
                    name="sigma_xx radius+d0",
                )
            )

        fig.add_trace(
            Scatter(
                x=[0.0, width],
                y=[load_x, load_x],
                mode="lines",
                line={"color": "black", "width": 2, "dash": "dash"},
                name="imposed_load_x",
            )
        )

        for key, fig in figures.items():
            file_name = f"{self.name}_{self._load_case.name}_{key}.html"
            plotly_save_and_show(
                fig, save=save, show=show, file_path=directory_path / file_name
            )

        return figures
