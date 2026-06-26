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

import re

import numpy as np
import pytest
from numpy import linspace
from numpy import power

import vimseo.lib_vimseo.solver_utilities as base_utils


@pytest.mark.fast
@pytest.mark.parametrize(
    "dict_limits",
    [
        ({"x_min": 0.1, "y_max": 3}),
        ({"x_max": 0.1, "y_min": 3}),
        ({"x_min": 0.1, "x_max": 0.3, "y_max": 3}),
        ({"x_min": 0.1, "y_min": 0.3, "y_max": 3}),
        ({"x_min": 0.1}),
        ({}),
    ],
)
def test_local_slope_computation_errors(dict_limits):
    """Check input error handling of base_utils.local_slope_computation()."""

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Either (x_min and x_max) or (y_min and y_max) should not be None"
        ),
    ):
        base_utils.local_slope_computation(
            x_curve=[0, 1, 2, 3],
            y_curve=[0, 11, 22, 33],
            **dict_limits,
        )


@pytest.mark.fast
@pytest.mark.parametrize("coeff_power", [0.6, 0.8, 1.0, 1.5, 2.0])
def test_local_slope_computation_values(tmp_wd, coeff_power):
    """Checks if base_utils.local_slope_computation() computes the slopes as expected, on a
    dummy analytical function."""

    def time2strain_function(time):
        # linear for the sake of sampling refinement
        return power(time, 1.0) * 0.1

    def strain2stress_function(strain):
        return 100.0 * power(strain, coeff_power)

    def stress2strain_function(stress):
        return power(0.01 * stress, 1.0 / coeff_power)

    def strain2stress_derivative(strain):
        return 100.0 * power(strain, coeff_power - 1.0) * coeff_power

    for e in [0, 0.001, 0.2, 1.0]:
        # check reciprocity of stress<->strain dummy functions
        assert e == pytest.approx(
            stress2strain_function(strain2stress_function(e)), rel=0.00001
        )

    # curves case study
    size = 200
    arbitrary_linear = linspace(0.0, 1.0, size)
    time_history = power(arbitrary_linear, 1.0)
    strain_history = time2strain_function(time_history)
    stress_history = strain2stress_function(strain_history)

    # modulus_e0005_e025
    computed_modulus_e005_e025 = base_utils.local_slope_computation(
        x_curve=strain_history,
        y_curve=stress_history,
        x_min=0.0005,
        x_max=0.0025,
        method="average",
    )
    ext_1 = strain2stress_derivative(0.0005)
    ext_2 = strain2stress_derivative(0.0025)
    if ext_2 >= ext_1:
        mini, maxi = ext_1 - 0.0001, ext_2 + 0.0001
    else:
        mini, maxi = ext_2 - 0.0001, ext_1 + 0.0001
    assert mini < computed_modulus_e005_e025 < maxi
    assert computed_modulus_e005_e025 == pytest.approx(
        (strain2stress_function(0.0025) - strain2stress_function(0.0005))
        / (0.0025 - 0.0005),
        rel=0.01,
    )

    # modulus_10_50
    index_max_stress = np.argmax(stress_history * 0.8)
    strain_at_max_strength = strain_history[index_max_stress]

    strain_10p = 0.10 * strain_at_max_strength
    strain_50p = 0.50 * strain_at_max_strength
    stress_10p = strain2stress_function(strain_10p)
    stress_50p = strain2stress_function(strain_50p)

    computed_modulus_10_50 = base_utils.local_slope_computation(
        x_curve=strain_history,
        y_curve=stress_history,
        x_min=strain_10p,
        x_max=strain_50p,
        method="regression",
    )

    ext_1 = strain2stress_derivative(strain_10p)
    ext_2 = strain2stress_derivative(strain_50p)
    mini = min(ext_1, ext_2) - 0.0001
    maxi = max(ext_1, ext_2) + 0.0001
    assert mini < computed_modulus_10_50 < maxi
    assert computed_modulus_10_50 == pytest.approx(
        (stress_50p - stress_10p) / (strain_50p - strain_10p), rel=0.1
    )
