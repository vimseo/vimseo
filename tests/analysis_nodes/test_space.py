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
from vimseo.api import create_model
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


def _get_parameters(space_analysis_node, name):
    """Return the parameters of the distribution of a variable."""
    distribution = space_analysis_node.parameter_space.distributions[name]
    return pytest.approx(list(distribution.distribution.getParameter()))


def test_update(tmp_wd):
    """Check that the space of parameters can be updated without ``execute``, as in
    the examples of :class:`.SpaceAnalysisNode`."""
    space_analysis_node = SpaceAnalysisNode()
    space_analysis_node.update(
        "OTNormalDistribution",
        "FromCenterAndCov",
        center_values={"force_relative_location": 0.5},
        cov=0.05,
    )
    assert space_analysis_node.parameter_space.variable_names == [
        "force_relative_location"
    ]
    assert _get_parameters(space_analysis_node, "force_relative_location") == [
        0.5,
        0.025,
    ]

    space_analysis_node.update(
        "OTTriangularDistribution",
        "FromMinAndMax",
        minimum_values={"young_modulus": 1e5},
        maximum_values={"young_modulus": 1.5e5},
        center_value_expr="0.25 * mini + 0.75 * maxi",
    )
    assert space_analysis_node.parameter_space.variable_names == [
        "force_relative_location",
        "young_modulus",
    ]
    assert _get_parameters(space_analysis_node, "young_modulus") == [
        1e5,
        1.375e5,
        1.5e5,
    ]

    model = create_model("BendingTestAnalytical", "Cantilever")
    space_analysis_node.update(
        "OTTriangularDistribution",
        "FromModelMinAndMax",
        model=model,
        variable_names=["young_modulus"],
        use_default_values_as_center=True,
    )
    assert _get_parameters(space_analysis_node, "young_modulus") == [
        1.9e5,
        2.1e5,
        2.3e5,
    ]


def test_update_from_statistics(tmp_wd):
    """Check that the space of parameters can be replaced by the one of a
    :class:`.StatisticsResult` without ``execute``."""
    space_for_sample_generation = ParameterSpace()
    space_for_sample_generation.add_random_variable(
        "x1",
        "OTDistribution",
        interfaced_distribution="Normal",
        parameters=(1.0, 0.05),
    )
    samples = space_for_sample_generation.compute_samples(n_samples=10)
    statistics_analysis_node = StatisticsAnalysisNode()
    statistics_analysis_node._options["tested_distributions"] = ["Normal"]
    statistics_analysis_node.execute(
        dataset=Dataset.from_array(samples, variable_names=["x1"])
    )

    space_analysis_node = SpaceAnalysisNode()
    space_analysis_node.update(
        "OTNormalDistribution", "FromCenterAndCov", center_values={"x": 0.5}, cov=0.05
    )
    space_analysis_node.update(statistics=statistics_analysis_node.result)
    assert space_analysis_node.parameter_space.variable_names == ["x1"]


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
