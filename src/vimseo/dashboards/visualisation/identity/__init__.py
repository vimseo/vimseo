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

"""Visual identity information."""

from __future__ import annotations

from pathlib import Path

import vimseo.dashboards.visualisation.identity as visu_identity

VISUALISATION_IDENTITY_PATH = Path(visu_identity.__path__[0])

# General definitions:
rgb_purple = (148, 120, 255)  # Define the RGB color (coorporate purple)
hex_purple = "#{:02x}{:02x}{:02x}".format(*rgb_purple)  # Convert RGB to hexadecimal

rgb_green = (0, 210, 77)  # Define the RGB color (coorporate green)
hex_green = "#{:02x}{:02x}{:02x}".format(*rgb_green)  # Convert RGB to hexadecimal

IDENTITY_COLORS = {"green": hex_green, "purple": hex_purple}
