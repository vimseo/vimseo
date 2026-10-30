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

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset

import vimseo.analysis_nodes as analysis_nodes
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.analysis_nodes.space.space_analysis_node import (
    _get_fitted_distribution_parameters,
)
from vimseo.analysis_nodes.space.space_analysis_node import update_space_from_statistics
from vimseo.analysis_nodes.statistics.statistics_analysis_node import (
    StatisticsAnalysisNode,
)
from vimseo.utilities.test_utils import check_result_visualization

ANALYSIS_NODE_PATH = Path(analysis_nodes.__path__[0])


@pytest.mark.parametrize(
    ("distribution_name", "distribution_options"),
    [
        ("Normal", (1.0, 0.05)),
        ("Uniform", (0.0, 2.0)),
        ("WeibullMin", (1.0, 2.0, 1.5)),
        ("Exponential", (1.0, 0.0)),
    ],
)
def test_space_from_statistics(tmp_wd, distribution_name, distribution_options):
    """Check that a parameter space is correctly filled from
    a :class:`.StatisticsResult`."""
    variable_name = "x1"
    space_for_sample_generation = ParameterSpace()
    space_for_sample_generation.add_random_variable(
        variable_name,
        "OTDistribution",
        interfaced_distribution=distribution_name,
        parameters=distribution_options,
    )
    samples = space_for_sample_generation.compute_samples(n_samples=10)
    dataset = Dataset.from_array(samples, variable_names=[variable_name])

    statistics_analysis_node = StatisticsAnalysisNode()
    # restrain the tested distribution to those handled in the SpaceAnalysisNode.
    statistics_analysis_node._options["tested_distributions"] = [distribution_name]
    statistics_analysis_node.execute(dataset=dataset)

    assert (
        statistics_analysis_node.result.analysis.distributions[variable_name].name
        == distribution_name
    )

    parameter_space = ParameterSpace()
    update_space_from_statistics(parameter_space, statistics_analysis_node.result)
    fitted_distribution = statistics_analysis_node.result.analysis.distributions[
        variable_name
    ].value
    assert (
        parameter_space.distributions[variable_name].marginals[0].vimseo_settings.name
        == distribution_name
    )
    assert parameter_space.distributions[variable_name].marginals[
        0
    ].vimseo_settings.parameters == _get_fitted_distribution_parameters(
        fitted_distribution
    )


def test_get_fitted_distribution_parameters_scipy_fallback():
    """A distribution with no ``getParameter`` (SciPy) falls back to ``.args``."""

    class _FakeNativeDistribution:
        args = (1.0, 2.0)

    class _FakeDistribution:
        distribution = _FakeNativeDistribution()

    assert _get_fitted_distribution_parameters(_FakeDistribution()) == (1.0, 2.0)


def test_save_and_load_json(tmp_wd):
    """Check that a space analysis can be saved and that a new instance can be created
    and loaded from saved data.

    A plot can be generated from the new instance.
    """
    space_analysis_node = SpaceAnalysisNode()
    # At least two variables are necessary to plot the parameter space as a scatter
    # matrix.
    center_values = {"x": 0.5, "y": 1.0}
    space_analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values=center_values,
        cov=0.05,
    )
    space_analysis_node.save_results(file_format="json")

    results = space_analysis_node.load_results(
        space_analysis_node.working_directory / "SpaceAnalysisNode_result.json"
    )
    results.plot(directory_path=space_analysis_node.working_directory, save=True)
    assert (space_analysis_node.working_directory / "scatter_matrix.png").is_file()


def test_result_visualization(tmp_wd):
    """Check that a space analysis node result can be visualized once loaded from a file."""
    space_analysis_node = SpaceAnalysisNode()
    space_analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    check_result_visualization(space_analysis_node.result, "visualization")
    assert set(space_analysis_node.result.to_dataframes()["parameter_space"].index) == {
        "x",
        "y",
    }
