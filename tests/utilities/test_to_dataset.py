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

import pytest
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from numpy import isnan
from numpy.testing import assert_allclose
from pandas import DataFrame

from vimseo.utilities.datasets import resolve_io_groups
from vimseo.utilities.datasets import to_dataset

pytestmark = pytest.mark.fast


def test_flat_mapping_of_scalars():
    """Check that a mapping of scalars lands in the default group."""
    dataset = to_dataset({"dx": [1.0, 0.5, 0.25], "sigma": [3.0, 3.5, 3.7]})

    assert isinstance(dataset, IODataset)
    assert dataset.group_names == [Dataset.DEFAULT_GROUP]
    assert dataset.variable_names == ["dx", "sigma"]
    assert dataset.variable_names_to_n_components == {"dx": 1, "sigma": 1}
    assert_allclose(
        dataset.get_view(variable_names="dx").to_numpy().ravel(), [1.0, 0.5, 0.25]
    )


def test_flat_mapping_with_a_vector():
    """Check that a 2D array is stored as a multi-component variable."""
    dataset = to_dataset({
        "x1": [1.0, 2.0],
        "x3": array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
    })

    assert dataset.variable_names_to_n_components == {"x1": 1, "x3": 3}
    assert_allclose(
        dataset.get_view(variable_names="x3").to_numpy(),
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
    )


def test_ragged_vectors_are_nan_padded():
    """Check that vectors of different lengths are padded with NaNs."""
    dataset = to_dataset({
        "x1": [1.0, 2.0],
        "x3": [array([1.0, 2.0]), array([3.0, 4.0, 5.0])],
    })

    assert dataset.variable_names_to_n_components["x3"] == 3
    values = dataset.get_view(variable_names="x3").to_numpy()
    assert_allclose(values[0, :2], [1.0, 2.0])
    assert isnan(values[0, 2])
    assert_allclose(values[1], [3.0, 4.0, 5.0])


def test_scalar_is_broadcast_over_the_entries():
    """Check that a scalar is repeated for every entry."""
    dataset = to_dataset({"h": [1.0, 2.0, 3.0], "length": 600.0, "case": "Cantilever"})

    assert_allclose(
        dataset.get_view(variable_names="length").to_numpy().ravel(), [600.0] * 3
    )
    assert (
        dataset.get_view(variable_names="case").to_numpy().ravel().tolist()
        == ["Cantilever"] * 3
    )


def test_nested_mapping_defines_the_groups():
    """Check that the top-level keys of a nested mapping are the group names."""
    dataset = to_dataset({
        "inputs": {"h": [1.0, 2.0]},
        "outputs": {"f": [10.0, 20.0]},
    })

    assert dataset.input_names == ["h"]
    assert dataset.output_names == ["f"]


def test_mono_index_dataframe():
    """Check that a plain DataFrame lands in the default group."""
    dataset = to_dataset(DataFrame({"dx": [1.0, 0.5], "sigma": [3.0, 3.5]}))

    assert dataset.group_names == [Dataset.DEFAULT_GROUP]
    assert dataset.variable_names == ["dx", "sigma"]


def test_dataframe_with_the_group_convention():
    """Check that the ``name{group}`` column convention is still honored."""
    dataset = to_dataset(
        DataFrame({"dx{inputs}": [1.0, 0.5], "s{outputs}": [3.0, 3.5]})
    )

    assert dataset.input_names == ["dx"]
    assert dataset.output_names == ["s"]


def test_dataset_is_returned_unchanged():
    """Check that an existing dataset is passed through."""
    source = IODataset.from_array(
        [[1.0, 2.0]],
        variable_names=["a", "b"],
        variable_names_to_group_names={"a": "inputs", "b": "outputs"},
    )

    assert to_dataset(source) is source


def test_plain_dataset_is_wrapped_as_an_io_dataset():
    """Check that a ``Dataset`` is accepted where an ``IODataset`` is expected."""
    source = Dataset.from_array([[1.0, 2.0]], variable_names=["a", "b"])
    dataset = to_dataset(source)

    assert isinstance(dataset, IODataset)
    assert dataset.variable_names == ["a", "b"]


def test_inconsistent_number_of_entries():
    """Check that variables of different lengths are rejected."""
    with pytest.raises(ValueError, match="all the variables must have the same number"):
        to_dataset({"a": [1.0, 2.0], "b": [1.0, 2.0, 3.0]})


def test_too_many_dimensions():
    """Check that data with more than two dimensions is rejected."""
    with pytest.raises(ValueError, match="has 3 dimensions"):
        to_dataset({"a": array([[[1.0]]])})


def test_unsupported_type():
    """Check that an unsupported type is rejected."""
    with pytest.raises(TypeError, match="Cannot build a dataset"):
        to_dataset(42)


def test_explicit_names_resolve_the_groups():
    """Check that ``input_names`` and ``output_names`` split the default group."""
    dataset = to_dataset(
        {"h": [1.0, 2.0], "f": [10.0, 20.0], "batch": [1, 1]},
        input_names=["h"],
        output_names=["f"],
    )

    assert dataset.input_names == ["h"]
    assert dataset.output_names == ["f"]
    assert dataset.get_variable_names(Dataset.DEFAULT_GROUP) == ["batch"]


def test_resolve_io_groups_from_a_model():
    """Check that the roles are read from the grammars of the model."""
    from vimseo.api import create_model

    model = create_model("BendingTestAnalytical", "Cantilever")
    dataset = resolve_io_groups(
        to_dataset({
            "height": [10.0, 15.0],
            "width": [10.0, 10.0],
            "reaction_forces": [-12.0, -40.0],
            "batch": [1, 2],
        }),
        model=model,
    )

    assert dataset.input_names == ["height", "width"]
    assert dataset.output_names == ["reaction_forces"]
    assert dataset.get_variable_names(Dataset.DEFAULT_GROUP) == ["batch"]


def test_resolve_io_groups_leaves_a_grouped_dataset_unchanged():
    """Check that a dataset already declaring its groups is not touched."""
    source = IODataset.from_array(
        [[1.0, 2.0]],
        variable_names=["a", "b"],
        variable_names_to_group_names={"a": "inputs", "b": "outputs"},
    )

    assert resolve_io_groups(source, input_names=["b"]) is source


def test_resolve_io_groups_without_any_role():
    """Check the error raised when the roles cannot be resolved."""
    with pytest.raises(ValueError, match="Cannot tell the inputs from the outputs"):
        resolve_io_groups(to_dataset({"a": [1.0]}))
