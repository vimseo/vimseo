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

from typing import TYPE_CHECKING

import numpy as np

from vimseo.core.load import LoadDirectionLiteral
from vimseo.core.load import LoadType

if TYPE_CHECKING:
    from vimseo.core.load_case import Load

DIR_MAP = {
    LoadDirectionLiteral.LL: 0,
    LoadDirectionLiteral.TT: 1,
    LoadDirectionLiteral.ZZ: 2,
    LoadDirectionLiteral.LT: 3,
    LoadDirectionLiteral.LZ: 4,
    LoadDirectionLiteral.TZ: 5,
}


def c_load_vectors_normed(load: Load):

    strain_component = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    stress_component = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    # VIMSEO vector ordering = Abaqus implicit convention
    map_load_dir_2_vector_index = {
        LoadDirectionLiteral.LL: 0,
        LoadDirectionLiteral.TT: 1,
        LoadDirectionLiteral.ZZ: 2,
        LoadDirectionLiteral.LT: 3,
        LoadDirectionLiteral.LZ: 4,
        LoadDirectionLiteral.TZ: 5,
    }

    index_vector = map_load_dir_2_vector_index[load.direction]

    if load.type == LoadType.STRAIN:
        strain_component[index_vector] = 1.0
    elif load.type == LoadType.STRESS:
        stress_component[index_vector] = 1.0
    else:
        msg = f"Incorrect load type: {load.type}."
        raise ValueError(msg)

    return strain_component, stress_component


def c_strain_vector_normed(load: Load):
    strain_component, _ = c_load_vectors_normed(load.direction, load.type)
    return strain_component


def c_stress_vector_normed(load: Load):
    _, stress_component = c_load_vectors_normed(load.direction, load.type)
    return stress_component


def c_index_vector(load: Load):
    # VIMSEO vector ordering = Abaqus implicit convention
    return DIR_MAP[load.direction]


def i_load_vectors_normed(load: Load):
    return c_load_vectors_normed(load)


def i_strain_vector_normed(load: Load):
    return c_strain_vector_normed(load)


def i_stress_vector_normed(load: Load):
    return c_stress_vector_normed(load)


def i_index_vector(load: Load):
    return c_index_vector(load)
