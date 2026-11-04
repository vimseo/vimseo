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

from numpy import array
from numpy import empty

from vimseo.core.components.base_component import BaseComponent

LOGGER = logging.getLogger(__name__)


class PreBendingTestAnalytical_Cantilever(BaseComponent):
    """Preprocessor for the load case Cantilever."""

    USE_JOB_DIRECTORY = False

    def __init__(self, **options):
        super().__init__(**options)
        self.default_input_data.update({
            "length": array([600.0]),
            "width": array([30.0]),
            "height": array([40.0]),
            "imposed_displacement": array([-5.0]),
            "relative_load_location": array([1.0]),
        })

    def _run(self, input_data):
        # load inputs:
        height = input_data["height"][0]
        width = input_data["width"][0]
        length = input_data["length"][0]
        imposed_displacement = input_data["imposed_displacement"][0]
        relative_load_location = input_data["relative_load_location"][0]
        young_modulus = input_data["young_modulus"][0]

        # compute the location of the load:
        x_f = relative_load_location * length

        # compute the second moment of area:
        second_moment_of_area = width * height**3 / 12.0

        # compute reaction force:
        force = (
            3 * young_modulus * second_moment_of_area * imposed_displacement / (x_f**3)
        )

        # compute the breakpoints of the piecewise-linear moment
        if x_f == length:
            m_grid = array([0.0, length])
            moment = array([-force * length, 0.0])
        else:
            m_grid = array([0.0, x_f, length])
            moment = array([-force * x_f, 0.0, 0.0])

        return {
            "second_moment_of_area": array([second_moment_of_area]),
            "load_location": array([x_f]),
            "reaction_forces": array([force]),
            "boundary": array([0.0]),
            "solver": array(["IVP"]),
            "moment_profile": moment,
            "position_profile_for_moment": m_grid,
        }


class PreBendingTestAnalytical_ThreePoints(BaseComponent):
    """Preprocessor for the load case ThreePoints."""

    USE_JOB_DIRECTORY = False

    def __init__(self, **options):
        super().__init__(**options)
        self.default_input_data.update({
            "length": array([600.0]),
            "width": array([30.0]),
            "height": array([40.0]),
            "imposed_displacement": array([-5.0]),
            "relative_support_location": array([0.5]),
        })

    def _run(self, input_data):
        height = input_data["height"][0]
        width = input_data["width"][0]
        length = input_data["length"][0]
        imposed_displacement = input_data["imposed_displacement"][0]
        relative_support_location = input_data["relative_support_location"][0]
        young_modulus = input_data["young_modulus"][0]

        support_location = empty(2)
        support_location[0] = (0.5 - relative_support_location) * length
        support_location[1] = (0.5 + relative_support_location) * length

        x_f = 0.5 * length

        second_moment_of_area = width * height**3 / 12.0

        support_length = support_location[1] - support_location[0]
        a = x_f - support_location[0]
        b = support_length - a

        force = (
            6
            * support_length
            * young_modulus
            * second_moment_of_area
            * imposed_displacement
        ) / (b * a * (support_length**2 - b**2 - a**2))

        m_grid = array([support_location[0], x_f, support_location[1]])
        moment = array([
            0.0,
            force * a * b / support_length,
            0.0,
        ])

        return {
            "second_moment_of_area": array([second_moment_of_area]),
            "load_location": array([x_f]),
            "reaction_forces": array([force]),
            "boundary": array([0.0, 0.0, 0.0, 0.0]),
            "solver": array(["BVP"]),
            "moment_profile": moment,
            "position_profile_for_moment": m_grid,
            "support_location": array(support_location),
        }
