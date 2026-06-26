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

"""A model in asymptotic convergence by construction.

Notations are taken from:
https://asmedigitalcollection.asme.org/verification/article/7/3/031005/1146443/Confidence-Intervals-for-Richardson-Extrapolation
"""

from __future__ import annotations

from gemseo.disciplines.analytic import AnalyticDiscipline
from numpy import atleast_1d

from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.core.model_metadata import MetaDataNames

ORDER = 2
mock_convergence_discipline = AnalyticDiscipline({
    "a_h": "a - a_n * h**n - a_m * h**m",
    "n_dof": "1. / h**3",
    MetaDataNames.cpu_time.name: "1.0",
})
mock_convergence_discipline.default_input_data = {
    "a": atleast_1d(1.0),
    "a_n": atleast_1d(0.1),
    "h": atleast_1d(2),
    "n": atleast_1d(ORDER),
    "a_m": atleast_1d(0.0),
    "m": atleast_1d(ORDER + 1),
}


class MockConvergence(BaseDisciplineModel):
    _DISCIPLINE = mock_convergence_discipline
    _EXPECTED_LOAD_CASE = "Dummy"
