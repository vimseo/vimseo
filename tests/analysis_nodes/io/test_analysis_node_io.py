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

from gemseo.datasets.io_dataset import IODataset
from pandas import DataFrame

from vimseo.analysis_nodes.io.reader_file_dataset import ReaderFileGemseoDataset
from vimseo.analysis_nodes.io.reader_file_result import BaseFileReaderSettings
from vimseo.analysis_nodes.io.reader_file_result import ResultFileReaderAnalysisNode
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
