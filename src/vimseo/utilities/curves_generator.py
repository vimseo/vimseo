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

from typing import TYPE_CHECKING

import numpy as np
from gemseo import create_discipline
from numpy import linspace

if TYPE_CHECKING:
    from collections.abc import Iterable
    from numbers import Number


def str_to_func(expression: str):
    """Create a python  function from a string analytical expression."""

    def f(x):
        # return eval(expression)

        disc = create_discipline(
            "AnalyticDiscipline", name="analytic", expressions={"y": expression}
        )

        x_array = np.atleast_1d(x)
        y_array = np.zeros(x_array.size)
        for i in range(len(x_array)):
            xx = np.atleast_1d(x_array[i])
            out = disc.execute({"x": xx})
            y_array[i] = out["y"][0]

        return y_array

    return f


def get_history(
    list_expressions: Iterable[str] = (),
    support: np.ndarray | Iterable[Number] = (),
    nb_points=50,
):
    """Builds a curve y-values by stacking transformation expressions."""
    if len(support) == 0:
        support = linspace(0.0, 1.0, nb_points)
    hist = support.copy()
    for expression in list_expressions:
        hist = str_to_func(expression)(hist)

    return hist


# defining elementary transformation expressions
expressions_convexity = {"convex": "x**2.1", "concave": "x**0.54", "flat": "x"}
expressions_oscillate = {
    "monotonous": "x",
    "half_drop": "sin(x*0.75*pi)",
    "half_period": "sin(x*pi)",
    "one_period": "sin(2*x*pi)",
}
