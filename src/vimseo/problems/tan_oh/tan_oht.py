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

import logging
from typing import TYPE_CHECKING
from typing import ClassVar

from composipy import LaminateProperty
from composipy import OrthotropicMaterial
from meshio import Mesh
from numpy import arange
from numpy import arctan2
from numpy import array
from numpy import atleast_1d
from numpy import column_stack
from numpy import linspace
from numpy import meshgrid
from numpy import nan
from numpy import pi
from numpy import sqrt
from numpy import zeros
from plotly.graph_objs import Scatter

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.lib_vimseo.tan_lib import tan_model
from vimseo.lib_vimseo.tan_lib import tan_model_grid
from vimseo.material.material import Material
from vimseo.material_lib import MATERIAL_LIB_DIR
from vimseo.utilities.fields import extract_line
from vimseo.utilities.plotting_utils import plotly_save_and_show

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from pathlib import Path

    from vimseo.core.load_case import LoadCase

LOGGER = logging.getLogger(__name__)

NOMINAL_GRID_SIZE = 100

#: Geometry (``d0``, ``radius``, ``width``, ``length``, ``thickness``) is in mm.
#: ``load`` and the ply material (moduli, strengths) are in MPa -- see
#: ``MATERIAL_FILE`` -- so the resulting stresses (``sigma_xx``, ``sigma_yy``,
#: ``sigma_xy``, ``sigma_xx_r``, ``sigma_xx_d0``) are also in MPa.
DEFAULT_INPUT_DATA = {
    "d0": atleast_1d(0.71),
    "radius": atleast_1d(3.175),
    "width": atleast_1d(32.0),
    "length": atleast_1d(80.0),
    "load": array([1000.0]),
    "grid_size": atleast_1d(float(NOMINAL_GRID_SIZE)),
    # Ply angles in degrees, as floats so they are continuous (differentiable)
    # variables -- the stacking drives c_strat (see ``compute_c_strat``).
    "layup": array([0.0, 45.0, -45.0, 90.0, 90.0, -45.0, 45.0, 0.0]),
}

#: Single-ply thickness, mm (consistent with the other geometric inputs above).
PLY_THICKNESS = 0.125

# The ply material (E1, E2, G12, nu12, strengths, all in MPa) lives in a JSON
# next to its grammar; the grammar makes the properties model inputs (see the
# components), and the material provides their default values.
MATERIAL_FILE = MATERIAL_LIB_DIR / "plane_orthotropic_ply.json"
MATERIAL_GRAMMAR_FILE = MATERIAL_LIB_DIR / "plane_orthotropic_ply_grammar.json"
material = Material.from_json(MATERIAL_FILE)

# Material property names driving the (elastic) membrane stiffness c_strat.
STIFFNESS_PROPERTY_NAMES = ("E1", "E2", "G12", "nu12")

total_thickness = len(DEFAULT_INPUT_DATA["layup"]) * PLY_THICKNESS
DEFAULT_INPUT_DATA["thickness"] = atleast_1d(total_thickness)


def compute_c_strat(layup, e1, e2, g12, nu12):
    """Effective membrane stiffness ``A / total_thickness`` from ply angles + material.

    Classical lamination theory (via composipy). ``c_strat`` is therefore a
    *derived* quantity of ``layup`` and the ply elastic constants,
    not a free input -- this removes the ambiguity of passing an inconsistent
    ``(c_strat, layup)`` pair. The differentiable JAX counterpart is
    :func:`vimseo.lib_vimseo.tan_lib_jax.c_strat_from_layup`.
    """
    ply = OrthotropicMaterial(e1=e1, e2=e2, v12=nu12, g12=g12, thickness=PLY_THICKNESS)
    laminate = LaminateProperty(layup, ply)
    return array(laminate.A) / (len(layup) * PLY_THICKNESS)


class TanRun_Tension(BaseComponent):
    """An Open Hole Tension model based on Tan theory (#open-hole-plate-model-tan-model).

    No grammar is defined for the material (and thus no bounds).
    """

    USE_JOB_DIRECTORY = True

    auto_detect_grammar_files = False
    default_grammar_type = "JSONGrammar"

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
        d0 = input_data["d0"][0]
        radius = input_data["radius"][0]
        grid_size = input_data["grid_size"][0]
        n_x = int(grid_size)
        n_y = int(grid_size)
        dx = length / (n_x - 1)
        dy = width / (n_y - 1)

        # ``load`` is the far-field applied stress, MPa (same unit as the ply
        # material -- see the module docstring above).
        load = array([input_data["load"][0], 0.0, 0.0]) / thickness

        c_strat = compute_c_strat(
            input_data["layup"],
            *(input_data[name][0] for name in STIFFNESS_PROPERTY_NAMES),
        )

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

        # Create quad connectivity. Node index at (i, j) = i * n_y + j.
        i_quad, j_quad = meshgrid(arange(n_x - 1), arange(n_y - 1), indexing="ij")
        i_quad = i_quad.ravel()
        j_quad = j_quad.ravel()
        quads = column_stack([
            i_quad * n_y + j_quad,
            (i_quad + 1) * n_y + j_quad,
            (i_quad + 1) * n_y + (j_quad + 1),
            i_quad * n_y + (j_quad + 1),
        ])

        # Evaluate the Tan solution on the whole grid at once (vectorised), then
        # blank out the points falling inside the hole.
        x_0 = xx - 0.5 * length
        y_0 = yy - 0.5 * width
        r = sqrt(x_0**2 + y_0**2)
        theta = arctan2(y_0, x_0)

        flux_n = tan_model_grid(
            r.ravel(), theta.ravel(), load, c_strat, radius, width
        ).reshape(n_x, n_y, 3)
        flux_n[r < radius + d0] = nan

        flatten_flux = flux_n.reshape(-1, 3)  # shape (nx*ny, 3)

        flux_field = Mesh(
            points=points,
            cells=[("quad", quads)],
            point_data={
                "N_xx": flatten_flux[:, 0],
                "N_yy": flatten_flux[:, 1],
                "N_xy": flatten_flux[:, 2],
                # sigma_* are membrane stresses, MPa.
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
    default_grammar_type = "JSONGrammar"

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

        input_names = [
            "length",
            "width",
            "radius",
            "d0",
            "dx",
            "dy",
            "load",
            "thickness",
        ]

        self.input_grammar.update_from_data({
            name: array([0.0]) for name in input_names
        })
        # The stacking drives c_strat (computed here), needed to evaluate the
        # stress directly at the hole edge (see ``_run``).
        self.input_grammar.update_from_data({"layup": DEFAULT_INPUT_DATA["layup"]})
        input_names.append("layup")

        for name in input_names:
            self.input_grammar.required_names.add(name)

        self._flux_components = ["sigma_xx", "sigma_yy", "sigma_xy", "Distance"]
        self._line_name = "line_center"
        line_output_names = [
            "line_center_y",
            "line_center_sigma_xx",
            "line_center_sigma_yy",
            "line_center_sigma_xy",
            "line_center_Distance",
        ]
        self.output_grammar.update_from_names(line_output_names)

        self.output_grammar.update_from_names(["sigma_xx_r", "sigma_xx_d0"])

    def _run(self, input_data):
        length = input_data["length"][0]
        width = input_data["width"][0]
        radius = input_data["radius"][0]
        d0 = input_data["d0"][0]
        thickness = input_data["thickness"][0]
        c_strat = compute_c_strat(
            input_data["layup"],
            *(input_data[name][0] for name in STIFFNESS_PROPERTY_NAMES),
        )
        # ``load`` is the far-field applied stress, MPa.
        load = array([input_data["load"][0], 0.0, 0.0]) / thickness

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

        # sigma_xx (MPa) just past the hole edge, evaluated directly on the Tan
        # solution (r = radius [+ d0], theta = pi/2 is the transverse center
        # line). This is differentiable and consistent with the analytic
        # Jacobian of ``TanOpenHole`` (see ``_compute_jacobian``), unlike the
        # former pyvista/scipy extraction of the discretised field.
        output_data["sigma_xx_r"] = atleast_1d(
            thickness * tan_model(radius, 0.5 * pi, load, c_strat, radius, width)[0]
        )
        output_data["sigma_xx_d0"] = atleast_1d(
            thickness
            * tan_model(radius + d0, 0.5 * pi, load, c_strat, radius, width)[0]
        )

        # TODO: compute reserve factor based on strength criteria instead of just returning 1.0
        output_data["reserve_factor"] = atleast_1d(1.0)

        return output_data


class TanOpenHole(IntegratedModel):
    """An Open Hole model based on Tan theory.

    The model provides an *analytic* membrane stress field for a plate with a
    circular hole (see the :ref:`Tan model reference
    <open-hole-plate-model-tan-model>`). The field is nonetheless evaluated on
    a grid whose resolution is driven by the ``grid_size`` input: the grid has
    ``grid_size`` points per direction, so a larger ``grid_size`` gives a
    finer grid. Because the solution is analytic, the values stored at the grid nodes
    are exact. What a coarse grid degrades is any quantity post-processed from the
    grid values.
    """

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
                    material_grammar_file=MATERIAL_GRAMMAR_FILE,
                    material=material,
                ),
                PostFieldExtraction(
                    load_case=LoadCaseFactory().create(load_case_name),
                    fields_from_file=self.FIELDS_FROM_FILE,
                    material_grammar_file=MATERIAL_GRAMMAR_FILE,
                    material=material,
                ),
            ],
            **options,
        )

    #: Scalar outputs and physical inputs handled by :meth:`_compute_jacobian`.
    _JACOBIAN_OUTPUTS: ClassVar[Sequence[str]] = ("sigma_xx_r", "sigma_xx_d0")
    _JACOBIAN_SCALAR_INPUTS: ClassVar[Sequence[str]] = (
        "load",
        "radius",
        "width",
        "d0",
        "thickness",
    )

    def _compute_jacobian(self, input_names=(), output_names=()):
        """Analytic Jacobian of the hole-edge stresses via the JAX kernel.

        Fills ``self.jac[output][input]`` for ``sigma_xx_r`` / ``sigma_xx_d0``
        with respect to ``load``, ``radius``, ``width``, ``d0``, ``thickness``,
        ``layup`` and the ply elastic constants (``E1``, ``E2``,
        ``G12``, ``nu12``), using the differentiable
        :mod:`~vimseo.lib_vimseo.tan_lib_jax` (requires the ``jax`` extra). The
        outputs are evaluated directly on the Tan solution, consistently with
        ``PostFieldExtraction``.

        ``c_strat`` is a derived quantity (classical lamination theory from
        ``layup`` and the material constants), so the ply-angle and
        material Jacobians go through the full chain ``(stacking, material) ->
        c_strat -> sigma`` and are genuine derivatives of the discipline output
        (validated by finite differences).
        """
        import jax

        from vimseo.lib_vimseo import tan_lib_jax as tan_jax

        data = self.get_input_data()
        load_x = float(data["load"][0])
        radius = float(data["radius"][0])
        width = float(data["width"][0])
        d0 = float(data["d0"][0])
        angles = array(data["layup"], dtype=float)
        stiffness = tuple(float(data[name][0]) for name in STIFFNESS_PROPERTY_NAMES)

        c_strat = array(compute_c_strat(angles, *stiffness), dtype=float)
        jac_scalar = jax.jacobian(tan_jax.scalar_outputs, argnums=(0, 1, 2, 3, 4))(
            load_x, radius, width, d0, float(data["thickness"][0]), c_strat
        )

        self._init_jacobian(input_names, output_names)
        for out_index, output_name in enumerate(self._JACOBIAN_OUTPUTS):
            if output_name not in self.jac:
                continue
            row = self.jac[output_name]
            for in_index, input_name in enumerate(self._JACOBIAN_SCALAR_INPUTS):
                if input_name in row:
                    row[input_name] = array([[float(jac_scalar[in_index][out_index])]])

        # d(sigma)/d(stacking, E1, E2, G12, nu12) through the CLT chain
        # (stacking, material) -> c_strat -> sigma.
        layup_inputs = ("layup", *STIFFNESS_PROPERTY_NAMES)
        if any(
            name in self.jac.get(output_name, {})
            for output_name in self._JACOBIAN_OUTPUTS
            for name in layup_inputs
        ):
            # argnums 4..8 map to (angles, e1, e2, g12, nu12).
            jac_layup = jax.jacobian(
                tan_jax.scalar_outputs_from_layup, argnums=(4, 5, 6, 7, 8)
            )(load_x, radius, width, d0, angles, *stiffness)
            for out_index, output_name in enumerate(self._JACOBIAN_OUTPUTS):
                row = self.jac.get(output_name)
                if row is None:
                    continue
                for arg_index, input_name in enumerate(layup_inputs):
                    if input_name in row:
                        row[input_name] = array(
                            jac_layup[arg_index][out_index]
                        ).reshape(1, -1)

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
