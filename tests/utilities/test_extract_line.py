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

"""
Tests for the extract_line function using a toy VTU file.

The toy mesh is a 2D XY plane [0,1] x [0,1] with:
  - a scalar field : p(x, y) = x + y
  - a vector field : u(x, y) = (x, y, 0)

Analytical values are known, which allows verifying
the interpolation along the extraction line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
import pyvista as pv

from vimseo.utilities.fields import extract_line  # adjust according to your module

if TYPE_CHECKING:
    from pathlib import Path


# =============================================================================
# FIXTURE : toy VTU file generation
# =============================================================================


@pytest.fixture(scope="module")
def toy_vtu(tmp_path_factory) -> Path:
    """
    Generates a 2D VTU mesh on [0,1] x [0,1] with known analytical fields.

    Fields:
      p(x, y) = x + y          (scalar)
      u(x, y) = (x, y, 0)      (vector)
    """
    tmp_path = tmp_path_factory.mktemp("vtu")
    vtu_path = tmp_path / "toy.vtu"

    # Structured 11x11 grid on [0,1] x [0,1]
    n = 11
    x = np.linspace(0, 1, n)
    y = np.linspace(0, 1, n)
    xx, yy = np.meshgrid(x, y)

    # 3D points (z=0 for a 2D plane)
    points = np.column_stack([
        xx.ravel(),
        yy.ravel(),
        np.zeros(n * n),
    ])

    # Build unstructured mesh (quads)
    cells = []
    cell_types = []
    for j in range(n - 1):
        for i in range(n - 1):
            p0 = j * n + i
            p1 = p0 + 1
            p2 = p0 + n + 1
            p3 = p0 + n
            cells.extend([4, p0, p1, p2, p3])  # 4 = number of nodes per quad
            cell_types.append(pv.CellType.QUAD)

    mesh = pv.UnstructuredGrid(cells, cell_types, points)

    # Analytical fields at nodes
    mesh.point_data["p"] = points[:, 0] + points[:, 1]  # p = x + y
    mesh.point_data["u"] = points.copy()  # u = (x, y, 0)
    mesh.point_data["u"][:, 2] = 0.0

    mesh.save(str(vtu_path))
    return vtu_path


# =============================================================================
# IMPORT of the function under test
# =============================================================================


# =============================================================================
# TESTS
# =============================================================================


def test_returns_expected_keys(self, toy_vtu):
    """Result contains the expected keys."""
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.5, 0.0),
        point_b=(1.0, 0.5, 0.0),
    )
    assert "coords" in result
    assert "dist" in result
    assert "p" in result
    assert "u" in result


def test_coords_shape(self, toy_vtu):
    """Coordinates array has the expected shape."""
    n_points = 50
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.5, 0.0),
        point_b=(1.0, 0.5, 0.0),
        n_points=n_points,
    )
    assert result["coords"].shape == (n_points + 1, 3)
    assert result["dist"].shape == (n_points + 1,)


def test_dist_starts_at_zero(self, toy_vtu):
    """Curvilinear distance starts at 0."""
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.0, 0.0),
        point_b=(1.0, 0.0, 0.0),
    )
    assert result["dist"][0] == pytest.approx(0.0, abs=1e-10)


def test_dist_ends_at_segment_length(self, toy_vtu):
    """Curvilinear distance ends at the segment length."""
    pa = np.array([0.0, 0.0, 0.0])
    pb = np.array([1.0, 0.0, 0.0])
    expected_length = np.linalg.norm(pb - pa)  # = 1.0

    result = extract_line(str(toy_vtu), point_a=tuple(pa), point_b=tuple(pb))
    assert result["dist"][-1] == pytest.approx(expected_length, abs=1e-10)


def test_scalar_field_horizontal_line(self, toy_vtu):
    """
    Horizontal line at y=0.5 : p(x, 0.5) = x + 0.5
    Verifies interpolation of scalar field p.
    """
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.5, 0.0),
        point_b=(1.0, 0.5, 0.0),
        n_points=100,
    )
    x_coords = result["coords"][:, 0]
    p_values = result["p"]
    p_expected = x_coords + 0.5  # p = x + y = x + 0.5

    np.testing.assert_allclose(p_values, p_expected, atol=1e-6)


def test_scalar_field_vertical_line(self, toy_vtu):
    """
    Vertical line at x=0.5 : p(0.5, y) = 0.5 + y
    Verifies interpolation of scalar field p.
    """
    result = extract_line(
        str(toy_vtu),
        point_a=(0.5, 0.0, 0.0),
        point_b=(0.5, 1.0, 0.0),
        n_points=100,
    )
    y_coords = result["coords"][:, 1]
    p_values = result["p"]
    p_expected = 0.5 + y_coords

    np.testing.assert_allclose(p_values, p_expected, atol=1e-6)


def test_scalar_field_diagonal_line(self, toy_vtu):
    """
    Diagonal line from (0,0) to (1,1) : p(t, t) = 2t
    """
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.0, 0.0),
        point_b=(1.0, 1.0, 0.0),
        n_points=100,
    )
    x_coords = result["coords"][:, 0]
    y_coords = result["coords"][:, 1]
    p_values = result["p"]
    p_expected = x_coords + y_coords

    np.testing.assert_allclose(p_values, p_expected, atol=1e-6)


def test_vector_field(self, toy_vtu):
    """
    Vector field u = (x, y, 0) on horizontal line y=0.5 :
    u_x(x, 0.5) = x, u_y(x, 0.5) = 0.5
    """
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.5, 0.0),
        point_b=(1.0, 0.5, 0.0),
        n_points=100,
    )
    x_coords = result["coords"][:, 0]
    u_values = result["u"]  # shape (n_points, 3)

    np.testing.assert_allclose(u_values[:, 0], x_coords, atol=1e-6)  # u_x = x
    np.testing.assert_allclose(u_values[:, 1], 0.5, atol=1e-6)  # u_y = 0.5
    np.testing.assert_allclose(u_values[:, 2], 0.0, atol=1e-6)  # u_z = 0


def test_field_selection(self, toy_vtu):
    """Only requested fields are returned."""
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.5, 0.0),
        point_b=(1.0, 0.5, 0.0),
        fields=["p"],
    )
    assert "p" in result
    assert "u" not in result


def test_missing_field_warning(self, toy_vtu, capsys):
    """A non-existent field triggers a warning and is ignored."""
    result = extract_line(
        str(toy_vtu),
        point_a=(0.0, 0.5, 0.0),
        point_b=(1.0, 0.5, 0.0),
        fields=["p", "nonexistent_field"],
    )
    captured = capsys.readouterr()
    assert "WARN" in captured.out
    assert "nonexistent_field" in captured.out
    assert "p" in result
    assert "nonexistent_field" not in result


def test_default_points_use_mesh_bounds(self, toy_vtu):
    """Without point_a/point_b, mesh bounds are used as defaults."""
    result = extract_line(str(toy_vtu))
    coords = result["coords"]

    # First point should be close to the mesh min corner
    assert coords[0, 0] == pytest.approx(0.0, abs=1e-6)
    assert coords[0, 1] == pytest.approx(0.0, abs=1e-6)

    # Last point should be close to the mesh max corner
    assert coords[-1, 0] == pytest.approx(1.0, abs=1e-6)
    assert coords[-1, 1] == pytest.approx(1.0, abs=1e-6)
