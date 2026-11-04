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

import logging

import numpy as np
from numpy import array
from scipy.interpolate import interp1d

from vimseo.core.components.base_component import BaseComponent

LOGGER = logging.getLogger(__name__)


class PostBendingTestAnalytical(BaseComponent):
    """Post processor for the analytical bending test model."""

    def _run(self, input_data):
        input_data = self.get_input_data()
        deflection = input_data["deflection_profile"]
        position = input_data["position_profile_for_deflection"]

        index_max_deflection = np.argmax(abs(deflection))
        return {
            "deflection_at_load_point": interp1d(position, deflection)(
                input_data["load_location"]
            ),
            "deflection_profile": deflection,
            "position_profile_for_deflection": position,
            # The signed value of largest magnitude.
            "maximum_deflection": array([deflection[index_max_deflection]]),
            "location_max_deflection": array([position[index_max_deflection]]),
            "moment_profile": input_data["moment_profile"],
            "position_profile_for_moment": input_data["position_profile_for_moment"],
            "reaction_forces": input_data["reaction_forces"],
            "error_code": array([0]),
        }


class PostBendingTestAnalytical_Cantilever(PostBendingTestAnalytical):
    """Extraction of the maximum force at the free end of the beam, and of the
    profiles of the deflection and of the moment along the beam."""


class PostBendingTestAnalytical_ThreePoints(PostBendingTestAnalytical):
    """Extraction of the maximum force, and of the profiles of the deflection and of
    the moment along the beam."""
