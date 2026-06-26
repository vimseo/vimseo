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

# Copyright (c) 2022 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Ludovic BARRIERE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

from gemseo.core.base_factory import BaseFactory

from vimseo.tools.lib.space_builders import SpaceBuilder


class SpaceBuilderFactory(BaseFactory):
    """Space builder factory to create a parameter space builder from a name or a
    class."""

    _CLASS = SpaceBuilder
    _PACKAGE_NAMES = ("vimseo.tools.lib",)
