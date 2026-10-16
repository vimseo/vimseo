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

import re

import pytest
from gemseo import get_available_doe_algorithms
from gemseo.algos.doe.factory import DOELibraryFactory
from gemseo.algos.parameter_space import ParameterSpace
from numpy import array
from numpy.testing import assert_allclose


@pytest.fixture
def star_doe():
    """The star DOE library."""
    return DOELibraryFactory().create("StarDOE")


@pytest.fixture
def variables_space():
    """A space with a bounded variable, a half-bounded one and a random one."""
    space = ParameterSpace()
    space.add_variable("a", lower_bound=0.0, upper_bound=10.0, value=2.0)
    space.add_variable("b", lower_bound=-1.0, value=1.0)
    space.add_random_variable("c", "OTNormalDistribution", mu=3.0, sigma=0.5)
    return space


def test_available():
    """Check that the star DOE is a GEMSEO DOE algorithm."""
    assert "StarDOE" in get_available_doe_algorithms()


def test_two_sided(star_doe, variables_space):
    """Check a two-sided star around the current values, with physical steps.

    For the normal variable, the step is relative to its mean, not to a quantile.
    """
    samples = star_doe.compute_doe(variables_space)
    assert_allclose(
        samples,
        array([
            [2.0, 1.0, 3.0],
            [2.1, 1.0, 3.0],
            [2.0, 1.05, 3.0],
            [2.0, 1.0, 3.15],
            [1.9, 1.0, 3.0],
            [2.0, 0.95, 3.0],
            [2.0, 1.0, 2.85],
        ]),
    )


def test_one_sided(star_doe, variables_space):
    """Check a one-sided star with a partial center and a relative step."""
    samples = star_doe.compute_doe(
        variables_space, center={"a": 4.0}, relative_step=0.1, two_sided=False
    )
    assert_allclose(
        samples,
        array([
            [4.0, 1.0, 3.0],
            [4.4, 1.0, 3.0],
            [4.0, 1.1, 3.0],
            [4.0, 1.0, 3.3],
        ]),
    )


def test_zero_center(star_doe, caplog):
    """Check the steps of the components whose center is zero."""
    space = ParameterSpace()
    space.add_variable("a", lower_bound=-1.0, upper_bound=3.0, value=0.0)
    space.add_variable("b", lower_bound=-1.0, value=0.0)
    space.add_random_variable("c", "OTNormalDistribution", mu=0.0, sigma=2.0)
    samples = star_doe.compute_doe(space, two_sided=False, fallback_step=0.3)
    assert_allclose(
        samples,
        array([
            [0.0, 0.0, 0.0],
            [0.2, 0.0, 0.0],
            [0.0, 0.3, 0.0],
            [0.0, 0.0, 0.1],
        ]),
        atol=1e-12,
    )
    assert "the range of its bounds" in caplog.text
    assert "the fallback step, as it has no scale" in caplog.text
    assert "the standard deviation of its distribution" in caplog.text


def test_zero_center_and_equal_bounds(star_doe):
    """Check that a zero center between equal bounds does not give a zero step.

    The fallback step is used instead, which leaves the bounds.
    """
    space = ParameterSpace()
    space.add_variable("a", lower_bound=0.0, upper_bound=0.0, value=0.0)
    with pytest.raises(ValueError, match=re.escape("outside the bounds of ['a']")):
        star_doe.compute_doe(space)


def test_vector(star_doe):
    """Check a star over a vector variable."""
    space = ParameterSpace()
    space.add_variable("x", size=2, lower_bound=0.0, upper_bound=10.0, value=[1.0, 2.0])
    samples = star_doe.compute_doe(space, two_sided=False)
    assert_allclose(samples, array([[1.0, 2.0], [1.05, 2.0], [1.0, 2.1]]))


def test_outside_bounds(star_doe, variables_space):
    """Check that a star going outside a defined bound raises an error."""
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The star DOE goes outside the bounds of ['a']; "
            "reduce the relative step or move the center."
        ),
    ):
        star_doe.compute_doe(variables_space, center={"a": 9.9})


def test_unknown_center(star_doe, variables_space):
    """Check that a center with an unknown variable raises an error."""
    with pytest.raises(ValueError, match=re.escape("The variables ['d']")):
        star_doe.compute_doe(variables_space, center={"d": 1.0})


def test_random_center_is_mean(star_doe, variables_space):
    """Check that the center of a random variable is the mean of its distribution,
    not its current value, which a previous DOE may have set to its best sample."""
    variables_space.set_current_variable("c", array([4.0]))
    samples = star_doe.compute_doe(variables_space, two_sided=False)
    assert_allclose(samples[0], [2.0, 1.0, 3.0])


def test_random_vector_center_is_mean(star_doe):
    """Check the center of a random vector."""
    space = ParameterSpace()
    space.add_random_vector("x", "OTNormalDistribution", size=2, mu=[1.0], sigma=[0.1])
    samples = star_doe.compute_doe(space, two_sided=False)
    assert_allclose(samples, array([[1.0, 1.0], [1.05, 1.0], [1.0, 1.05]]))
