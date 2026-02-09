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

from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import array
from numpy import linspace
from numpy import ones
from pandas import DataFrame

from vimseo.tools.verification.solution_verification import (
    DiscretizationSolutionVerification,
)
from vimseo.tools.verification.solution_verification_case import (
    SolutionVerificationCase,
)


def test_solution_verification_case(tmp_wd):
    y_offset = linspace(0.0, 1.0, 3)
    results = []
    for offset in y_offset:
        verificator = DiscretizationSolutionVerification(
            directory_naming_method=DirectoryNamingMethod.NUMBERED,
        )
        df = DataFrame.from_dict({
            ("inputs", "h", 0): array([0.5, 0.4, 0.3, 0.2, 0.1]),
            ("outputs", "a_h", 0): array([1.5, 1.4, 1.3, 1.2, 1.1]) + offset,
            ("outputs", "y1", 0): ones(5),
            ("outputs", "cpu_time", 0): linspace(1.0, 2.0, 5),
        })
        results.append(
            verificator.execute(
                element_size_variable_name="h",
                output_name="a_h",
                simulated_data=df,
            )
        )

    tool = SolutionVerificationCase()
    result = tool.execute(results=results)
    tool.plot_results(result, save=True, show=False)
    assert tool.working_directory / "convergence_case_h_a_h.html"
    assert tool.working_directory / "cpu_time_compromise_a_h.html"

