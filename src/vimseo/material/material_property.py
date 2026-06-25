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

"""A material property."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from vimseo.utilities.distribution import DEFAULT_MIN_MAX
from vimseo.utilities.distribution import DistributionParameters

#: The distribution names a material property can be defined with,
#: ``""`` standing for a deterministic property.
SUPPORTED_DISTRIBUTIONS = ("", "Normal", "Uniform")


class MaterialProperty(BaseModel):
    """A material property."""

    name: str
    description: str = ""
    value: float
    lower_bound: float = -DEFAULT_MIN_MAX
    upper_bound: float = DEFAULT_MIN_MAX
    distribution: DistributionParameters = Field(
        default_factory=lambda: DistributionParameters()
    )

    @field_validator("distribution")
    @classmethod
    def _check_supported_distribution(
        cls, distribution: DistributionParameters
    ) -> DistributionParameters:
        """Reject distributions that a material property cannot handle."""
        if distribution.name not in SUPPORTED_DISTRIBUTIONS:
            msg = (
                f"Only deterministic, Normal and Uniform distributions are supported "
                f"for a material property, got a {distribution.name} distribution."
            )
            raise ValueError(msg)
        return distribution

    def model_post_init(self, __context: Any) -> None:
        """Set the distribution bounds equal to the property bounds."""
        if self.distribution:
            self.distribution.lower_bound = self.lower_bound
            self.distribution.upper_bound = self.upper_bound
