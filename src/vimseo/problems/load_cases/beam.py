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

from dataclasses import dataclass

from vimseo.core.load_case import LoadCase


@dataclass
class Beam_Cantilever(LoadCase):
    """A cantilever load case."""

    def get_bc_variable_names(self):
        return [
            "imposed_dplt",
            "relative_dplt_location",
        ]


@dataclass
class Beam_ThreePoints(LoadCase):
    """A three-points load case."""

    def get_bc_variable_names(self):
        return ["imposed_dplt", "relative_support_location"]


@dataclass
class Beam_FourPoints(LoadCase):
    """A four-points load case."""

    def get_bc_variable_names(self):
        return ["imposed_dplt", "relative_dplt_location", "relative_support_location"]
