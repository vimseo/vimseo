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
from openturns import RandomGenerator

from vimseo.analysis_nodes.base_result import assert_results_equal
from vimseo.analysis_nodes.statistics.statistics_analysis_node import (
    StatisticsAnalysisNode,
)
from vimseo.analysis_nodes.statistics.statistics_analysis_node import StatisticsInputs
from vimseo.analysis_nodes.statistics.statistics_analysis_node import StatisticsSettings
from vimseo.analysis_nodes.statistics.statistics_analysis_node import compute_ecdf
from vimseo.analysis_nodes.statistics.statistics_result import StatisticsResult
from vimseo.utilities.datasets import DatasetAddFromStatistics
from vimseo.utilities.distribution import DistributionParameters
from vimseo.utilities.test_utils import check_result_visualization


def test_fitting_default_options(tmp_wd):
    """Check that a uniform distribution is correctly inferred with default options."""
    # The samples are drawn by the global random generator of OpenTURNS: without a
    # seed, they depend on the tests executed before in the same process. With 100
    # samples, the minimum is above -0.475 in 8% of the draws, i.e. out of the
    # tolerance below; the seed makes the test reproducible.
    RandomGenerator.SetSeed(0)  # ruff: ignore[numpy-legacy-random]
    distribution_name = "Uniform"
    lower = -0.5
    upper = 0.5
    dataset = Dataset()
    dataset_manipulator = DatasetAddFromStatistics()
    dataset_manipulator.add_group(
        dataset,
        IODataset.INPUT_GROUP,
        ["x"],
        {"x": DistributionParameters(name=distribution_name, lower=lower, upper=upper)},
        100,
    )
    result = StatisticsAnalysisNode().execute(
        inputs=StatisticsInputs(dataset=dataset),
        settings=StatisticsSettings(tested_distributions=[distribution_name]),
    )
    assert result.best_fitting_distributions["x"] == distribution_name
    assert result.statistics["minimum"]["x"] == pytest.approx(lower, rel=0.05)
    assert result.statistics["maximum"]["x"] == pytest.approx(upper, rel=0.05)


def test_save_and_load_pickle(tmp_wd):
    """Check that a statistic analysis with custom options can be saved and plotted."""
    distribution_name = "Uniform"
    lower = -0.5
    upper = 0.5
    dataset = Dataset()
    dataset_manipulator = DatasetAddFromStatistics()
    dataset_manipulator.add_group(
        dataset,
        IODataset.INPUT_GROUP,
        ["x"],
        {"x": DistributionParameters(name=distribution_name, lower=lower, upper=upper)},
        100,
    )
    analysis_node = StatisticsAnalysisNode()
    result = analysis_node.execute(
        inputs=StatisticsInputs(dataset=dataset),
        settings=StatisticsSettings(tested_distributions=[distribution_name]),
    )
    result.plot(
        directory_path=analysis_node.working_directory, save=True, variable_names=["x"]
    )
    assert (analysis_node.working_directory / "criteria_x.png").is_file()


def test_from_uniform_sample(tmp_wd):
    """Check that a uniform distribution can be infered from a uniform sample."""
    uniform_dataset = Dataset.from_array([[1.0], [1.0], [1.0]], variable_names=["x"])
    result = StatisticsAnalysisNode().execute(
        inputs=StatisticsInputs(dataset=uniform_dataset),
        settings=StatisticsSettings(tested_distributions=["Uniform"]),
    )
    assert result.best_fitting_distributions["x"] == "Uniform"


def test_serialization(tmp_wd):
    """Check that a StatisticsResult can be serialized to hdf5."""
    uniform_dataset = Dataset.from_array([[1.0], [1.0], [1.0]], variable_names=["x"])
    result = StatisticsAnalysisNode().execute(
        inputs=StatisticsInputs(dataset=uniform_dataset),
        settings=StatisticsSettings(tested_distributions=["Uniform"]),
    )
    result.to_hdf5("result.hdf5")
    serialized_result = StatisticsResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)


def test_compute_ecdf():
    """The empirical CDF of a dataset is returned as a dataset of x/y curves."""
    dataset = Dataset.from_array([[1.0], [2.0], [3.0]], variable_names=["x"])
    ecdf = compute_ecdf(dataset, prefix="p")
    assert "p_x_x" in ecdf.variable_names
    assert "p_x_y" in ecdf.variable_names


def test_result_visualization(tmp_wd):
    """Check that a statistics result can be visualized once loaded from a file."""
    dataset = Dataset()
    DatasetAddFromStatistics().add_group(
        dataset,
        IODataset.INPUT_GROUP,
        ["x"],
        {"x": DistributionParameters(name="Uniform", lower=-0.5, upper=0.5)},
        100,
    )
    result = StatisticsAnalysisNode().execute(
        inputs=StatisticsInputs(dataset=dataset),
        settings=StatisticsSettings(tested_distributions=["Uniform"]),
    )
    check_result_visualization(result, "visualization")
    tables = result.to_dataframes()
    assert "x" in tables["statistics"].index
    assert "mean" in tables["statistics"].columns
