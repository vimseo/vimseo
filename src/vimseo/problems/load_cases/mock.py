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
from vimseo.tools.post_tools.plot_parameters import PlotParameters


@dataclass
class LC1(LoadCase):
    """A first mock load case."""


@dataclass
class LC2(LoadCase):
    """A second mock load case."""

    def get_plot_parameters(self):
        return PlotParameters(curves=[("y1", "y1_2")])


@dataclass
class Metallic_LC1(LoadCase):
    """A metallic LC1 load case."""
