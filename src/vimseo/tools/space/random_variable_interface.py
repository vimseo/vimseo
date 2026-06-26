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

from gemseo.uncertainty.distributions.base_distribution import (
    InterfacedDistributionSettings,
)

if TYPE_CHECKING:
    from gemseo.algos.parameter_space import ParameterSpace

    from vimseo.utilities.distribution import DistributionParameters

OPTIONS_PER_DISTRIBUTION = {
    "OTUniformDistribution": ("lower", "upper"),
    "OTNormalDistribution": ("mu", "sigma"),
    "OTTriangularDistribution": ("lower", "upper", "mode"),
    "SPUniformDistribution": ("lower", "upper"),
    "SPNormalDistribution": ("mu", "sigma"),
    "SPTriangularDistribution": ("lower", "upper", "mode"),
}


def add_random_variable_interface(
    parameter_space: ParameterSpace,
    variable_name: str,
    settings: DistributionParameters | InterfacedDistributionSettings,
    size: int = 1,
):
    """An interface to handle seamlessly the interfaces to
    :meth:`gemseo.algos.parameter_space.add_random_variable` for an OT distribution."""
    if isinstance(settings, InterfacedDistributionSettings):
        if size == 1:
            parameter_space.add_random_variable(
                variable_name,
                "OTDistribution",
                size=size,
                settings=settings,
            )
        else:
            msg = (
                f"Only scalars are handled for an "
                f"``InterfaceDistribution``. But variable {variable_name} "
                f"has dimension {size}."
            )
            raise ValueError(msg)
    else:
        if size == 1:
            parameter_space.add_random_variable(
                variable_name,
                size=size,
                distribution=f"OT{settings.name}Distribution",
                settings=settings,
            )
        else:
            parameters = {
                k: v
                for k, v in settings.model_dump().items()
                if k in OPTIONS_PER_DISTRIBUTION[f"OT{settings.name}Distribution"]
            }
            parameter_space.add_random_vector(
                variable_name,
                size=size,
                distribution=f"OT{settings.name}Distribution",
                **parameters,
            )
