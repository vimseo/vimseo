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

import numpy as np
from numpy import array
from scipy.interpolate import interp1d

from vimseo.core.components.base_component import BaseComponent

LOGGER = logging.getLogger(__name__)


class PostBendingTestAnalytical(BaseComponent):
    """Post processor for the analytical bending test model."""


class PostBendingTestAnalytical_Cantilever(PostBendingTestAnalytical):
    """Extraction of the maximum force at the free end of the beam and displacement grid
    and moment grid along the beam."""

    def _run(self, input_data):
        disp = input_data["dplt"]
        x_grid = input_data["dplt_grid"]
        x_f = input_data["imposed_dplt_location"]

        f = interp1d(x_grid, disp)
        dplt_at_f = f(x_f)
        max_dplt = max(abs(disp))
        index_max_dplt = np.argmax(abs(disp))
        max_dplt *= disp[index_max_dplt] / max_dplt
        location_max_dplt = x_grid[index_max_dplt]

        return {
            "dplt_at_force_location": dplt_at_f,
            "dplt": disp,
            "dplt_grid": x_grid,
            "maximum_dplt": np.array([max_dplt]),
            "location_max_dplt": np.array([location_max_dplt]),
            "moment": input_data["moment"],
            "moment_grid": input_data["moment_grid"],
            "reaction_forces": self.get_input_data()["reaction_forces"],
            "error_code": array([0]),
        }


class PostBendingTestAnalytical_ThreePoints(PostBendingTestAnalytical):
    """Extraction of the maximum force, displacement grid and moment grid along the
    beam."""

    def _run(self, input_data):
        disp = self.get_input_data()["dplt"]
        x_grid = self.get_input_data()["dplt_grid"]
        x_f = self.get_input_data()["imposed_dplt_location"]

        f = interp1d(x_grid, disp)
        dplt_at_f = f(x_f)
        max_dplt = max(abs(disp))
        index_max_dplt = np.argmax(abs(disp))
        max_dplt *= disp[index_max_dplt] / max_dplt
        location_max_dplt = x_grid[index_max_dplt]

        return {
            "dplt_at_force_location": dplt_at_f,
            "dplt": disp,
            "dplt_grid": x_grid,
            "maximum_dplt": np.array([max_dplt]),
            "location_max_dplt": np.array([location_max_dplt]),
            "moment": self.get_input_data()["moment"],
            "moment_grid": self.get_input_data()["moment_grid"],
            "reaction_forces": self.get_input_data()["reaction_forces"],
            "error_code": array([0]),
        }
