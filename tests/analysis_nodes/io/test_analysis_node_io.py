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

from vimseo.analysis_nodes.base_result import assert_results_equal
from vimseo.analysis_nodes.io.reader_file_dataset import ReaderFileGemseoDataset
from vimseo.analysis_nodes.io.reader_file_result import BaseFileReaderSettings
from vimseo.analysis_nodes.io.reader_file_result import ResultFileReaderAnalysisNode
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.analysis_nodes.space.space_analysis_node_result import (
    SpaceAnalysisNodeResult,
)
from vimseo.io.test_data import IO_DATA_DIR
from vimseo.utilities.datasets import SEP


def test_analysis_node_result_reader():
    analysis_node_name = "SpaceAnalysisNode"
    reader = ResultFileReaderAnalysisNode(analysis_node_name)
    result = reader.execute(
        settings=BaseFileReaderSettings(
            file_name=IO_DATA_DIR
            / "space_analysis_node"
            / "space_analysis_node_result.json",
            analysis_node_name=analysis_node_name,
        )
    )
    assert isinstance(result, SpaceAnalysisNodeResult)
    parameter_space = result.parameter_space
    assert parameter_space.variable_names == ["x", "y"]
    for name, (minimum, maximum) in {
        "x": (0.475, 0.525),
        "y": (0.95, 1.05),
    }.items():
        assert parameter_space.get_lower_bound(name) == pytest.approx([minimum])
        assert parameter_space.get_upper_bound(name) == pytest.approx([maximum])


def _read_space_result(analysis_node_name="SpaceAnalysisNode"):
    """Write the result of a space analysis node to HDF5, then read it back.

    Returns:
        The written result and the read result.
    """
    space_analysis_node = SpaceAnalysisNode()
    space_analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5},
        cov=0.05,
    )
    space_analysis_node.save_results()
    file_name = space_analysis_node.working_directory / (
        f"{space_analysis_node.name}_result.hdf5"
    )

    reader = ResultFileReaderAnalysisNode(analysis_node_name)
    result = reader.execute(
        settings=BaseFileReaderSettings(
            file_name=file_name, analysis_node_name=analysis_node_name
        )
    )
    return space_analysis_node.result, result


def test_analysis_node_result_reader_hdf5(tmp_wd):
    """Check that the data of a result read from an HDF5 file are the written ones
    (#39)."""
    written, read = _read_space_result()
    assert isinstance(read, SpaceAnalysisNodeResult)
    assert_results_equal(read.parameter_space, written.parameter_space)


@pytest.mark.xfail(
    strict=True,
    reason="The reader replaces the settings of the result it reads with its own.",
)
def test_analysis_node_result_reader_keeps_the_metadata(tmp_wd):
    """Check that a result read from an HDF5 file keeps its metadata."""
    written, read = _read_space_result()
    assert read.metadata.settings == written.metadata.settings


def test_gemseo_dataset_reader(tmp_wd):
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
    reader = ReaderFileGemseoDataset()
    read_dataset = reader.execute(
        file_name="dataset.csv",
    ).dataset
    assert DataFrame.equals(dataset, read_dataset)
