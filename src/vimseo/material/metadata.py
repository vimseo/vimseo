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

"""A metadata attached to a material relation."""

from __future__ import annotations

from dataclasses import dataclass

from vimseo.tools.base_metadata import BaseMetadata


@dataclass
class MaterialMetadata(BaseMetadata):
    """A metadata attached to a material relation."""

    author: str = ""
    """The author of the calibrated material relation."""

    source: str = ""
    """A description of the source of daa used to calibrate this material relation."""
