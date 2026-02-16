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
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.core.grammars.pydantic_grammar import PydanticGrammar
from numpy import array
from numpy import atleast_1d
from numpy import linspace
from pydantic import BaseModel

from vimseo.core.components.base_component import BaseComponent
from vimseo.utilities.fields import extract_line

if TYPE_CHECKING:
    from vimseo.core.load_case import LoadCase


LOGGER = logging.getLogger(__name__)


class PreCouette2DInputGrammar(BaseModel):
    """The input grammar for the Couette 2D model post-processor."""


class PreCouette2DOutputGrammar(BaseModel):
    """The output grammar for the Couette 2D model post-processor."""


class PostPyFR_Couette2D(BaseComponent):
    """Post process the Couette 2D case."""

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
        self.input_grammar.update_from_data({"error_code": atleast_1d(0)})
        self.input_grammar.required_names.add("error_code")

        self.output_grammar = PydanticGrammar(
            "grammar", model=PreCouette2DOutputGrammar
        )
        # self.output_grammar.update_from_data({"error_code": atleast_1d(0)})
        # self.output_grammar.required_names.add("error_code")

        line_data = {}
        # for t in linspace(0, 10, num=11):
        for t in linspace(0, 9, num=10):
            for field in ["velocity_0", "velocity_1", "density", "pressure"]:
                line_data[f"line_{field}_{int(t):03d}"] = array([0.0])

        line_data["line_y"] = array([0.0])
        line_data["line_distance"] = array([0.0])
        self.output_grammar.update_from_data(line_data)
        for name in line_data:
            self.output_grammar.required_names.add(name)

    def _run(self, input_data):
        """Post-run operations."""
        # Mapping name from PyFR to name in grammar:
        mapping = {
            "Velocity": "velocity",
            "Density": "density",
            "Pressure": "pressure",
        }

        output_data = {}

        files = self.job_directory.glob(pattern="*.pyfrs")
        print(f"Found pyfrs files: {files}.")
        for i, file in enumerate(files):
            suffix = file.name.split("-")[-1]
            suffix = suffix.split(".pyfrs")[0]

            # # temp
            # vtu_file = file
            # suffix = suffix.replace(".vtu", "")
            # # ----

            vtu_file = file.with_suffix(".vtu")
            print(f"Conversion de {file} en format VTU dans {vtu_file}")
            pyfrm_file = "couette-flow.pyfrm"
            pyfrs_filename = Path(file).name
            vtu_filename = Path(vtu_file).name
            subprocess.run(
                f"pyfr export {pyfrm_file} {pyfrs_filename} {vtu_filename}".split(),
                cwd=self._job_directory,
                capture_output=True,
            )
            print("Conversion terminée.")

            line = extract_line(
                vtu_file=vtu_file,
                point_a=(0.0, 0.0, 0.0),
                point_b=(0.0, 1.0, 0.0),
                n_points=200,
                fields=["Velocity", "Density", "y", "Distance", "Pressure"],
            )

            # Store constant data only for first file:
            if i == 0:
                output_data["line_y"] = line["coords"][:, 1]
                output_data["line_distance"] = line["Distance"]

            for field, mapped_field in mapping.items():
                if field == "Velocity":
                    # On suppose que Velocity est un champ vectoriel, et on prend sa composante x
                    for i in range(2):
                        output_data[f"line_{mapped_field}_{i}_{suffix}"] = line[field][
                            :, i
                        ]
                else:
                    output_data[f"line_{mapped_field}_{suffix}"] = line[field]

            # vtu_to_png([vtu_file], output_folder=self.job_directory, scalar_name="Velocity", clim=(0, 70))
            # vtu_to_png([vtu_file], output_folder=self.job_directory, scalar_name="Density", clim=(0, 1.2))

        return output_data
