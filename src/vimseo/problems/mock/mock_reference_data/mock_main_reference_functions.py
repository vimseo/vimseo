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

from numpy import array
from numpy import atleast_1d


def mock_model_lc1_overall_function(x1):
    """The overall input to output function representing the MockModel load case LC1."""
    return (x1 + 2) * 2 + 1


def mock_model_lc2_overall_function(x1, x1_2):
    """The overall input to output function representing the MockModel load case LC2."""
    y1 = (x1 + x1_2 + 2) * 2 + 1
    return y1, y1 + 1