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

from pathlib import Path
from re import escape

import pytest
from numpy import linspace
from numpy import zeros
from numpy.testing import assert_array_equal

from vimseo.utilities.curves import Curve


def test_curves(tmp_wd):
    """Check that a curve can be exported as a dictionary and plotted."""

    x = linspace(0, 1, 10)
    curve = Curve({"x": x, "y": 0.5 * x})
    curve_as_dict = curve.as_dict()
    assert_array_equal(curve_as_dict["x"], x)
    assert_array_equal(curve_as_dict["y"], 0.5 * x)

    curve.plot(save=True, show=False)
    assert Path("curve_y_vs_x.html").is_file()


@pytest.mark.parametrize(
    "value",
    [
        zeros((10,)),
        [0] * 10,
    ],
)
def test_curve_axis_update(value):
    """Check that the x and y axis of a curve can be set."""
    x = linspace(0, 1, 10)
    curve = Curve({"x": x, "y": 0.5 * x})
    curve.x = value
    curve.y = value


@pytest.mark.parametrize("value", [[0.0, 1.0], zeros((10, 1)), zeros((10, 2))])
def test_wrong_curve_axis_update(value):
    """Check that the x and y axis of a curve can be set."""
    x = linspace(0, 1, 10)
    curve = Curve({"x": x, "y": 0.5 * x})
    msg = "X axis should be an array of dimension 1 and length 10."
    with pytest.raises(ValueError, match=escape(msg)):
        curve.x = value
    msg = "Y axis should be an array of dimension 1 and length 10."
    with pytest.raises(ValueError, match=escape(msg)):
        curve.y = value
