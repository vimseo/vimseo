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
"""Settings of the star DOE."""

from __future__ import annotations

from collections.abc import Mapping

from gemseo.algos.doe.base_doe_settings import BaseDOESettings
from pydantic import Field
from pydantic import PositiveFloat


class StarDOE_Settings(BaseDOESettings):
    """The settings of the star DOE."""

    _TARGET_CLASS_NAME = "StarDOE"

    center: Mapping[str, float | list[float]] = Field(
        default={},
        description="The physical values of the variables at the center of the star. "
        "A variable missing from this mapping takes the mean of its distribution "
        "if it is random, otherwise its current value in the variables space. "
        "The current value of a random variable is not used, "
        "since a DOE sets it to its best sample.",
    )

    relative_step: PositiveFloat = Field(
        default=0.05,
        description=r"""The relative step :math:`\delta` of the star.

The physical step of the :math:`i`-th component is the first applicable rule among:

1. :math:`\delta|x_{0,i}|` if the center :math:`x_{0,i}` is not zero,
2. :math:`\delta\sigma_i` if the variable is random,
   where :math:`\sigma_i` is the standard deviation of its marginal distribution,
3. :math:`\delta(u_i-l_i)` if both bounds :math:`l_i` and :math:`u_i` are defined
   and different,
4. ``fallback_step`` otherwise.""",
    )

    two_sided: bool = Field(
        default=True,
        description="Whether to vary each component on both sides of the center. "
        "If ``True``, the DOE has :math:`2d+1` points and allows centered differences; "
        "otherwise, it has :math:`d+1` points.",
    )

    fallback_step: PositiveFloat = Field(
        default=0.05,
        description="The absolute step of a component whose center is zero, "
        "which is not random and has an undefined bound or equal bounds.",
    )
