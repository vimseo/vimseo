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

import pytest
from meshio import Mesh

from vimseo.tools.io.field_result import FieldResult
from vimseo.utilities.fields import MeshField


@pytest.fixture
def unit_square_mesh() -> Mesh:
    """A two-triangle unit square with a linear pressure MeshField."""
    return Mesh(
        points=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        cells=[("triangle", [[0, 1, 2], [0, 2, 3]])],
        point_data={"pressure": [0.0, 1.0, 2.0, 1.0]},
        cell_data={"rms_velocity": [[0.0, 1.0]]},
    )


def test_single_element(unit_square_mesh):
    """Check the behavior when passing a single MeshField."""
    result = FieldResult(fields=MeshField.from_mesh(unit_square_mesh))
    assert isinstance(result.fields, list)
