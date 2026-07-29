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
from numpy.testing import assert_allclose

from vimseo.utilities.fields import MeshField


# tests/utilities/test_MeshFields.py
@pytest.fixture
def unit_square_mesh() -> Mesh:
    """A two-triangle unit square with a linear pressure MeshField."""
    return Mesh(
        points=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        cells=[("triangle", [[0, 1, 2], [0, 2, 3]])],
        point_data={"pressure": [0.0, 1.0, 2.0, 1.0]},
    )


def test_from_mesh(unit_square_mesh):
    """Check that a MeshField is built from an already-read mesh."""
    field = MeshField.from_mesh(unit_square_mesh, "source.dat")
    assert field.path == "source.dat"
    assert field.point_variable_names == ["pressure"]
    assert_allclose(field.mesh_points, unit_square_mesh.points)


def test_from_mesh_without_path(unit_square_mesh):
    """Check that a MeshField can be built from a mesh with no file provenance."""
    assert MeshField.from_mesh(unit_square_mesh).path == ""


def test_load(tmp_wd, unit_square_mesh):
    """Check that a MeshField is loaded from a mesh file."""
    unit_square_mesh.write("mesh.vtk")
    field = MeshField.load("mesh.vtk")
    assert field.path == "mesh.vtk"
    assert_allclose(field.point_data["pressure"], [0.0, 1.0, 2.0, 1.0])
