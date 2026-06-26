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

"""The below ``AnalyticDiscipline`` implement explicit analytical laws for some output
variables of the ``BendingTestAnalytical``.

The underlying physics is exactly the same
as the ``BendingTestAnalytical`` for:
 - Cantilever load case
 - ThreePoints load case under the following boundary conditions:
    - "relative_dplt_location" = 0.5
    - "relative_support_location" = [0.0, 1.0]

These disciplines can serve as reference models for validation or verification.
"""

from __future__ import annotations

from gemseo.disciplines.analytic import AnalyticDiscipline

from vimseo.core.base_discipline_model import BaseDisciplineModel

bending_test_analytical_cantilever = AnalyticDiscipline({
    "reaction_forces": "3 * young_modulus * (width * height**3 / 12) * imposed_dplt"
    " / ((relative_dplt_location * length) ** 3)",
})

# More generic formulation to be copied from unit test of bending test analytical model.
bending_test_analytical_three_points = AnalyticDiscipline({
    "reaction_forces": "48 * young_modulus * (width * height**3 / 12) * "
    "imposed_dplt / length**3",
})


class AnalyticBendingTestCantilever(BaseDisciplineModel):
    _DISCIPLINE = bending_test_analytical_cantilever
    _EXPECTED_LOAD_CASE = "Cantilever"


class AnalyticBendingTestThreePoints(BaseDisciplineModel):
    _DISCIPLINE = bending_test_analytical_three_points
    _EXPECTED_LOAD_CASE = "ThreePoints"
