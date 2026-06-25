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
from numpy.ma.testutils import assert_array_equal
from pandas._testing import assert_frame_equal

from vimseo.utilities.datasets import assert_frame_equal_unordered
from vimseo.utilities.datasets import dataframe_to_dataset
from vimseo.utilities.datasets import dataset_to_dataframe


@pytest.fixture
def mock_dataset():
    """A mock dataset."""
    return Dataset.from_array(
        data=array([[0.0, 1.0, 2.0, 2.1, 3.0, 3.1], [4.0, 5.0, 6.0, 6.1, 7.0, 7.1]]),
        variable_names=["a[]", "b", "c[foo]", "d"],
        variable_names_to_group_names={
            "a[]": IODataset.INPUT_GROUP,
            "b": IODataset.OUTPUT_GROUP,
            "c[foo]": IODataset.OUTPUT_GROUP,
            "d": IODataset.OUTPUT_GROUP,
        },
        variable_names_to_n_components={"a[]": 1, "b": 1, "c[foo]": 2, "d": 2},
    )


@pytest.fixture
def mock_dataset_with_duplicated_names():
    """A mock dataset."""
    dataset = Dataset.from_array(
        data=array([[0.0, 2.0, 2.1, 3.0, 3.1], [4.0, 6.0, 6.1, 7.0, 7.1]]),
        variable_names=["a", "b", "c"],
        variable_names_to_group_names={
            "a": IODataset.OUTPUT_GROUP,
            "b": IODataset.OUTPUT_GROUP,
            "c": IODataset.OUTPUT_GROUP,
        },
        variable_names_to_n_components={"a": 1, "b": 2, "c": 2},
    )
    dataset.add_variable(
        variable_name="a", group_name=IODataset.INPUT_GROUP, data=[1.0, 5.0]
    )
    return dataset


def test_dataset_to_dataframe(mock_dataset):
    """Check that a GEMSEO dataset can be converted to a mono-index DataFrame."""
    df = dataset_to_dataframe(mock_dataset, suffix_by_group=True)
    assert list(df.columns.values) == [
        "a[]{inputs}",
        "b{outputs}",
        "c[foo]{outputs}[0]",
        "c[foo]{outputs}[1]",
        "d{outputs}[0]",
        "d{outputs}[1]",
    ]


def test_dataframe_to_dataset(mock_dataset):
    """Check that a GEMSEO Dataset can be converted to a mono-index DataFrame, keeping
    track of group and component information."""
    df = dataset_to_dataframe(mock_dataset, suffix_by_group=True)
    ds = dataframe_to_dataset(df)
    assert_frame_equal(mock_dataset, ds)


def test_dataframe_to_dataset_with_duplicated_names(mock_dataset_with_duplicated_names):
    """Check that a GEMSEO Dataset with repeated variable name in two groups can be
    converted to a mono-index DataFrame, keeping track of group and component
    information."""
    df = dataset_to_dataframe(mock_dataset_with_duplicated_names, suffix_by_group=True)
    ds = dataframe_to_dataset(df)

    assert ds.group_names == [IODataset.INPUT_GROUP, IODataset.OUTPUT_GROUP]
    assert ds.variable_names_to_n_components == {"a": 2, "b": 2, "c": 2}
    assert ds.get_variable_names(IODataset.INPUT_GROUP) == ["a"]
    assert ds.get_variable_names(IODataset.OUTPUT_GROUP) == ["a", "b", "c"]
    assert_array_equal(
        ds
        .get_view(variable_names=["a"], group_names=IODataset.INPUT_GROUP)
        .to_numpy()
        .ravel(),
        df[f"a{{{IODataset.INPUT_GROUP}}}"].to_numpy(),
    )
    assert_array_equal(
        ds
        .get_view(variable_names=["a"], group_names=IODataset.OUTPUT_GROUP)
        .to_numpy()
        .ravel(),
        df[f"a{{{IODataset.OUTPUT_GROUP}}}"].to_numpy(),
    )
    assert_array_equal(
        ds
        .get_view(variable_names=["b"], group_names=IODataset.OUTPUT_GROUP)
        .to_numpy()
        .T[0],
        df[f"b{{{IODataset.OUTPUT_GROUP}}}[0]"].to_numpy(),
    )


@pytest.mark.parametrize(
    ("variable_names", "expected_final_names"),
    [
        ([], ["a{inputs}", "b[0]", "b[1]", "c[0]", "c[1]", "a{outputs}"]),
        (["a"], ["a{inputs}", "a{outputs}"]),
        (["a", "b"], ["a{inputs}", "b[0]", "b[1]", "a{outputs}"]),
    ],
)
def test_dataset_with_duplicated_names_to_dataframe(
    mock_dataset_with_duplicated_names, variable_names, expected_final_names
):
    """Check that a GEMSEO dataset can be converted to a mono-index DataFrame.

    Duplicated names across groups are handled by suffixing with the group name between
    square brackets.
    """
    df = dataset_to_dataframe(
        mock_dataset_with_duplicated_names, variable_names=variable_names
    )
    assert list(df.columns.values) == expected_final_names


@pytest.mark.parametrize(
    "dataset_fixture",
    ["mock_dataset", "mock_dataset_with_duplicated_names"],
)
def test_dataset_to_dataframe_round_trip(dataset_fixture, request):
    """Test dataframe to dataset with equality of original data after round trip."""
    dataset = request.getfixturevalue(dataset_fixture)
    df = dataset_to_dataframe(dataset, suffix_by_group=True)
    round_trip_dataset = dataframe_to_dataset(df)
    assert_frame_equal_unordered(dataset, round_trip_dataset)
