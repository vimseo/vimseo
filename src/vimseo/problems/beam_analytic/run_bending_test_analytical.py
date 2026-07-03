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
from typing import ClassVar

from numpy import array
from numpy import linspace
from numpy import vstack
from numpy import zeros
from scipy.interpolate import interp1d

from vimseo.core.components.base_component import BaseComponent

LOGGER = logging.getLogger(__name__)


class RunBendingTestAnalytical(BaseComponent):
    """Drives the calculation of maximal displacement from loading and boundary
    conditions."""

    _X_NB_PTS: ClassVar[int] = 100

    def __init__(self, **options):
        super().__init__(**options)
        self.m_func = None
        self.E = None
        self.moment_inertia = None
        self.BC = None

    def _run(self, input_data):
        solver = input_data["solver"][0]
        self.BC = input_data["boundary"]
        moment = input_data["moment"]
        m_grid = input_data["moment_grid"]

        displacement, displacement_grid = self.solver_equations(
            input_data, m_grid, moment, solver
        )

        return {"dplt": displacement, "dplt_grid": displacement_grid}

    def solver_equations(self, input_data, m_grid, moment, solver):
        """

        Args:
            m_grid:
            moment:
            solver:

        Returns:

        """
        self.E = input_data["young_modulus"]
        self.moment_inertia = input_data["quadratic_moment"]
        self.build_moment_linear(m_grid, moment)

        x = linspace(m_grid[0], m_grid[-1], self._X_NB_PTS).flatten()

        if solver == "IVP":
            from scipy.integrate import solve_ivp

            res = solve_ivp(
                self.fun_scalar, array([x[0], x[-1]]), array([0.0, 0.0]), t_eval=x
            )
            w = res.y[0]

        elif solver == "BVP":
            from scipy.integrate import solve_bvp

            y = zeros((2, x.size))
            res = solve_bvp(self.fun_array, self.bc, x, y)
            w = res.sol(x)[0, :]

        return w, x

    def fun_scalar(self, x, y):
        """
        Suited for initial value solver
        Args:
            x:
            y:

        Returns:

        """
        moment = self.m_func(x)
        return [y[1], -moment / (self.E[0] * self.moment_inertia[0])]

    def fun_array(self, x, y):
        """
        Suited for boundary value problem.
        Args:
            x: (m, ) array of sorted x values
            y: (2, m) array, with y[0] and y[1] corresponding to 0th and 1st order
            derivatives of displacement

        Returns:
            1st and second derivatives of displacement in a (2, m) array
        """
        moment = self.m_func(x)
        return vstack((y[1], -moment / (self.E * self.moment_inertia)))

    def bc(self, ya, yb):
        return array([ya[0] - self.BC[0], yb[0] - self.BC[2]])

    def build_moment_linear(self, x, moment):
        self.m_func = interp1d(x, moment)
