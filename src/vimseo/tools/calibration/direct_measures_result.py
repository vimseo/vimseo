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

from collections.abc import Mapping

from numpy import ndarray

from vimseo.tools.base_result import BaseResult


class DirectMeasuresResult(BaseResult):
    """The result of a ``DirectMeasures`` tool."""

    direct_measures: Mapping[str, ndarray] | None = None
    """The direct measures."""

    mean_direct_measures: Mapping[str, float] | None = None
    """The mean value of the direct measures."""
