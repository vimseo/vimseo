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

from typing import Any


def rotate_list(a_list: list, first_elt: Any):
    """Rotate list element such that the first element matches ``first_first_elt``."""
    if first_elt not in a_list:
        msg = f"{first_elt} is not in {a_list}."
        raise ValueError(msg)

    i = a_list.index(first_elt)
    return a_list[i:] + a_list[:i]
