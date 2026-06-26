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

"""Builds a reference dataset from explicit imposed-force analytical beam model."""

from __future__ import annotations

from vimseo.api import create_model
from vimseo.problems.beam_explicit.analytical_laws import (
    analytic_bending_test_analytical_cantilever,
)
from vimseo.problems.beam_explicit.analytical_laws import (
    analytic_bending_test_analytical_three_points,
)
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.utilities.datasets import SEP

if __name__ == "__main__":
    analytic_bending_test_analytical = {
        "Cantilever": analytic_bending_test_analytical_cantilever,
        "ThreePoints": analytic_bending_test_analytical_three_points,
    }
    for load_case in ["Cantilever", "ThreePoints"]:
        model = analytic_bending_test_analytical[load_case]

        # Set default values to the default values of the analytical beam model.
        bending_test_analytical_model = create_model("BendingTestAnalytical", load_case)
        for name, value in bending_test_analytical_model.default_input_data.items():
            if name in model.default_input_data:
                model.default_input_data[name] = value

        # Check that all input variables have a default value.
        assert set(model.default_input_data.keys()) == set(model.input_grammar.names)

        space_tool = SpaceTool()
        retained_variables = model.input_grammar.names
        if load_case == "Cantilever":
            retained_variables.remove("relative_dplt_location")
        space_tool.update(
            "OTTriangularDistribution",
            "FromModelCenterAndCov",
            variable_names=retained_variables,
            use_default_values_as_center=True,
            model=model,
            cov=0.05,
        )
        if load_case == "Cantilever":
            space_tool.update(
                "OTTriangularDistribution",
                "FromCenterAndCov",
                center_values={"relative_dplt_location": 0.9},
                cov=0.05,
            )
        # Check that all input variables are in the space of parameters.
        assert set(space_tool.parameter_space.variable_names) == set(
            model.input_grammar.names
        )
        print(space_tool.parameter_space)

        tool = DOETool()
        tool.execute(model, space_tool.parameter_space, n_samples=10)
        tool.result.dataset.to_csv(f"explicit_beam_{load_case.lower()}.csv", sep=SEP)
