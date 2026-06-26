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
from gemseo.datasets.io_dataset import IODataset
from pandas import DataFrame

from vimseo.io.test_data import IO_DATA_DIR
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrame
from vimseo.tools.io.reader_file_dataset import ReaderFileGemseoDataset
from vimseo.utilities.datasets import SEP


def test_io_read_dataset(tmp_wd):
    """Check that a GEMSEO dataset can be read."""
    sample_1 = [0.0, 1.0, 2.0, 3.0]
    sample_2 = [0.5, 1.5, 2.5, 3.5]
    variable_names_to_n_components = {"x": 1, "y1": 1, "y2": 2}
    dataset = IODataset.from_array(
        [sample_1, sample_2],
        variable_names=["x", "y1", "y2"],
        variable_names_to_n_components=variable_names_to_n_components,
        variable_names_to_group_names={"x": "inputs", "y1": "outputs", "y2": "outputs"},
    )
    dataset.to_csv("dataset.csv", sep=SEP)
    assert DataFrame.equals(
        dataset, ReaderFileGemseoDataset().execute(file_name="dataset.csv").dataset
    )


def test_io_read_dataframe(tmp_wd):
    """Check that a Pandas DataFrame can be read."""
    sample_1 = [0.0, 1.0, 2.0]
    sample_2 = [0.5, 1.5, 2.5]
    variable_names = ["x", "y1", "y2"]
    variable_names_to_group_names = {"x": "inputs", "y1": "outputs", "y2": "outputs"}
    dataset = IODataset.from_array(
        [sample_1, sample_2],
        variable_names=variable_names,
        variable_names_to_group_names=variable_names_to_group_names,
    )
    df = dataset.copy()
    df.columns = dataset.get_columns()
    df.to_csv("dataframe.csv", sep=SEP, index=False)
    assert DataFrame.equals(
        dataset,
        ReaderFileDataFrame()
        .execute(
            variable_names=variable_names,
            variable_names_to_group_names=variable_names_to_group_names,
            file_name="dataframe.csv",
        )
        .dataset,
    )


@pytest.mark.parametrize(
    "filename",
    [
        "dataframe_vectors.csv",
        "dataframe_vectors_component_indexing.csv",
    ],
)
def test_io_read_dataframe_with_vectors(tmp_wd, filename):
    """Check that a Pandas DataFrame with vectors can be read."""
    sample_1 = [0.0, 1.0, 2.0, 3.0]
    sample_2 = [0.5, 1.5, 2.5, 3.5]
    variable_names = ["x", "y1", "y2"]
    variable_names_to_group_names = {"x": "inputs", "y1": "outputs", "y2": "outputs"}
    variable_names_to_n_components = {"y2": 2}
    dataset = IODataset.from_array(
        [sample_1, sample_2],
        variable_names=variable_names,
        variable_names_to_group_names=variable_names_to_group_names,
        variable_names_to_n_components=variable_names_to_n_components,
    )
    assert DataFrame.equals(
        dataset,
        ReaderFileDataFrame()
        .execute(
            variable_names=variable_names,
            variable_names_to_group_names=variable_names_to_group_names,
            variable_names_to_n_components=variable_names_to_n_components,
            file_name=IO_DATA_DIR / "dataset" / filename,
        )
        .dataset,
    )


@pytest.mark.skip(reason="Issue opened in GEMSEO")
def test_io_read_dataframe_infer_header(tmp_wd):
    """Check that a Pandas DataFrame with vectors can be read."""
    sample_1 = [0.0, 1.0, 2.0, 3.0]
    sample_2 = [0.5, 1.5, 2.5, 3.5]
    variable_names = ["x", "y1", "y2"]
    variable_names_to_group_names = {"x": "inputs", "y1": "outputs", "y2": "outputs"}
    variable_names_to_n_components = {"y2": 2}
    dataset = IODataset.from_array(
        [sample_1, sample_2],
        variable_names=variable_names,
        variable_names_to_group_names=variable_names_to_group_names,
        variable_names_to_n_components=variable_names_to_n_components,
    )
    assert DataFrame.equals(
        dataset,
        ReaderFileDataFrame()
        .execute(
            variable_names_to_group_names=variable_names_to_group_names,
            variable_names_to_n_components=variable_names_to_n_components,
            file_name=IO_DATA_DIR
            / "dataset"
            / "dataframe_vectors_component_indexing.csv",
        )
        .dataset,
    )
