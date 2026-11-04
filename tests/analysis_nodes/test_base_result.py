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

"""Tests for assert_results_equal, on which many other tests rely."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from gemseo.datasets.io_dataset import IODataset

from vimseo.analysis_nodes.base_result import BaseResult
from vimseo.analysis_nodes.base_result import assert_results_equal


@dataclass
class _Result(BaseResult):
    value: float = 0.0
    names: list[str] = field(default_factory=list)


class _NotComparable:
    def __eq__(self, other):
        msg = "not comparable"
        raise TypeError(msg)

    __hash__ = object.__hash__


def _dataset(value: float) -> IODataset:
    dataset = IODataset()
    dataset.add_variable("x", np.array([[1.0], [value]]), "inputs")
    return dataset


EQUAL = [
    ("a", "a"),
    (1, 1),
    (True, True),
    (None, None),
    (1.0, 1.0 + 1e-9),
    (float("nan"), float("nan")),
    ((1, 2), (1, 2)),
    ((1, 2), [1, 2]),
    ([np.array([1.0]), "a"], [np.array([1.0]), "a"]),
    ({"a": np.array([1.0, 2.0])}, {"a": np.array([1.0, 2.0])}),
    (np.array([1.0, 2.0]), np.array([1.0, 2.0])),
    (pd.DataFrame({"a": [1.0]}), pd.DataFrame({"a": [1.0]})),
    (_dataset(2.0), _dataset(2.0)),
    (_Result(value=1.0, names=["a"]), _Result(value=1.0, names=["a"])),
]

DIFFERENT = [
    ("a", "b"),
    (1, 2),
    (True, False),
    (None, 1),
    (1.0, 1.1),
    (1.0, float("nan")),
    (float("nan"), 1.0),
    ((1, 2), (1, 3)),
    ((1, 2), (1, 2, 3)),
    ((1, 2), "12"),
    ((np.array([1.0]),), (np.array([2.0]),)),
    ({"a": 1}, {"b": 1}),
    ({"a": 1}, {"a": 2}),
    (np.array([1.0, 2.0]), np.array([1.0, 3.0])),
    (pd.DataFrame({"a": [1.0]}), pd.DataFrame({"a": [2.0]})),
    (_dataset(2.0), _dataset(3.0)),
    (_Result(value=1.0), _Result(value=2.0)),
    (_Result(names=["a"]), _Result(names=["b"])),
    (_Result(), BaseResult()),
]


@pytest.mark.parametrize(("r1", "r2"), EQUAL)
def test_equal(r1, r2):
    """Check that equal objects are found equal."""
    assert_results_equal(r1, r2)


@pytest.mark.parametrize(("r1", "r2"), DIFFERENT)
def test_different(r1, r2):
    """Check that different objects are found different."""
    with pytest.raises(AssertionError):
        assert_results_equal(r1, r2)


def test_not_comparable():
    """Check that only the type of objects that cannot be compared is checked."""
    assert_results_equal(_NotComparable(), _NotComparable())
    with pytest.raises(AssertionError):
        assert_results_equal(_NotComparable(), 1)


def test_figures():
    """Check that only the type of the figures is checked."""
    figure_1, figure_2 = plt.figure(), plt.figure()
    try:
        assert_results_equal(figure_1, figure_2)
    finally:
        plt.close(figure_1)
        plt.close(figure_2)


def test_generic_metadata_ignored():
    """Check that the ``generic`` field of the metadata is not compared."""
    r1, r2 = _Result(), _Result()
    r1.metadata.generic["datetime"] = "01-01-2026_00-00-00"
    r2.metadata.generic["datetime"] = "02-01-2026_00-00-00"
    assert_results_equal(r1, r2)
