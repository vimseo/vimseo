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

from gemseo.core.grammars.pydantic_grammar import PydanticGrammar
from gemseo.utils.pydantic_ndarray import NDArrayPydantic
from numpy import atleast_1d
from pydantic import BaseModel

from vimseo.core.components.base_component import BaseComponent
from vimseo.problems.cfd.couette_2d.generate_mesh import generate_couette_mesh

if TYPE_CHECKING:
    from vimseo.core.load_case import LoadCase


LOGGER = logging.getLogger(__name__)

DEFAULT_INPUT_DATA = {
    "mu": atleast_1d(0.417),
    "prandtl": atleast_1d(0.72),
    "cp": atleast_1d(1005.0),
    "dt": atleast_1d(4e-5),
    "dx": atleast_1d(0.25),
    "u_w": atleast_1d(70.0),
}


class PreCouette2DInputGrammar(BaseModel):
    """The input grammar for the Couette 2D model."""

    mu: NDArrayPydantic[float]
    prandtl: NDArrayPydantic[float]
    cp: NDArrayPydantic[float]
    dt: NDArrayPydantic[float]
    dx: NDArrayPydantic[float]
    u_w: NDArrayPydantic[float]


class PreCouette2DOutputGrammar(BaseModel):
    """The output grammar for the Couette 2D model."""


class PrePyFR_Couette2D(BaseComponent):
    """Generates parametric mesh for the Couette 2D case."""

    default_grammar_type = "PydanticGrammar"

    def __init__(
        self,
        load_case: LoadCase,
        material_grammar_file="",
        material=None,
        check_subprocess: bool = False,
    ):
        super().__init__(load_case, material_grammar_file, material, check_subprocess)

        self.input_grammar = PydanticGrammar("grammar", model=PreCouette2DInputGrammar)
        self.output_grammar = PydanticGrammar(
            "grammar", model=PreCouette2DOutputGrammar
        )
        self.default_input_data = DEFAULT_INPUT_DATA

    def _run(self, input_data):
        """Pre-run operations."""
        # is_empty = not any(self.job_directory.iterdir())
        # if not is_empty:
        #     msg = f"{self.job_directory} should be empty."
        #     raise ValueError(msg)

        generate_couette_mesh(
            mesh_size=input_data["dx"][0],
            output=str(self.job_directory / "couette-flow.msh"),
        )

        return {}
