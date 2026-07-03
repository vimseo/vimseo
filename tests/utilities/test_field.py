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

"""Tests for the ``Field`` grid helpers ``to_structured_grid`` and ``probe``.

A toy rectangular structured grid carrying a linear field ``p(x, y) = x + 2 y``
is used, so bilinear interpolation is exact and the reshaped values are known.
"""

from __future__ import annotations

import numpy as np
import pytest

from vimseo.utilities.fields import Field


def _linear_field(nx: int = 3, ny: int = 4):
    """A rectangular (nx, ny) grid carrying ``p = x + 2 y``."""
    x = np.linspace(0.0, 2.0, nx)
    y = np.linspace(0.0, 3.0, ny)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    points = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(nx * ny)])
    values = xx.ravel() + 2.0 * yy.ravel()
    return points, values, x, y


def test_to_structured_grid_rectangular():
    """The component is reshaped onto its (rectangular) grid."""
    points, values, x, y = _linear_field()
    field = Field(mesh_points=points, point_data={"p": values})
    grid_x, grid_y, grid_z = field.to_structured_grid("p")
    np.testing.assert_allclose(grid_x, x)
    np.testing.assert_allclose(grid_y, y)
    assert grid_z.shape == (len(x), len(y))
    np.testing.assert_allclose(grid_z, x[:, None] + 2.0 * y[None, :])


def test_to_structured_grid_is_order_independent():
    """Shuffled node ordering still reconstructs the same grid."""
    points, values, x, y = _linear_field()
    perm = np.random.default_rng(0).permutation(len(values))
    field = Field(mesh_points=points[perm], point_data={"p": values[perm]})
    _, _, grid_z = field.to_structured_grid("p")
    np.testing.assert_allclose(grid_z, x[:, None] + 2.0 * y[None, :])


def test_to_structured_grid_blanks_missing_nodes():
    """A nan-valued node stays nan on the reshaped grid."""
    points, values, _, _ = _linear_field()
    values = values.copy()
    values[2] = np.nan
    field = Field(mesh_points=points, point_data={"p": values})
    _, _, grid_z = field.to_structured_grid("p")
    assert np.isnan(grid_z).sum() == 1


def test_probe_is_exact_on_a_linear_field():
    """Bilinear interpolation is exact for a linear field."""
    points, values, _, _ = _linear_field()
    field = Field(mesh_points=points, point_data={"p": values})
    assert field.probe("p", 1.0, 1.5) == pytest.approx(1.0 + 2.0 * 1.5)


def test_probe_outside_grid_returns_nan():
    """A probe point outside the grid returns nan."""
    points, values, _, _ = _linear_field()
    field = Field(mesh_points=points, point_data={"p": values})
    assert np.isnan(field.probe("p", 10.0, 10.0))
