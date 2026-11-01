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

import json

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from numpy import array

from vimseo.analysis_nodes.space.random_variable_interface import (
    add_random_variable_interface,
)
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.analysis_nodes.space.space_analysis_node_result import (
    SpaceAnalysisNodeResult,
)
from vimseo.api import create_model
from vimseo.io.space_io import SpaceAnalysisNodeFileIO
from vimseo.io.test_data import IO_DATA_DIR
from vimseo.utilities.distribution import DistributionParameters
from vimseo.utilities.distribution import InterfacedDistributionSettings
from vimseo.utilities.distribution_utils import check_distribution


@pytest.mark.parametrize("as_byte", [True, False])
@pytest.mark.parametrize(
    "from_buffer",
    [True, False],
)
def test_read(from_buffer, as_byte):
    """Check that a space analysis node result can be instantiated from a readable result file."""
    file_path = IO_DATA_DIR / "space_analysis_node" / "space_analysis_node_result.json"

    if from_buffer:
        mode = "rb" if as_byte else "r"
        with open(file_path, mode) as f:
            result = SpaceAnalysisNodeFileIO().read_buffer(f.read())
    else:
        result = SpaceAnalysisNodeFileIO().read(file_path)

    with open(file_path) as f:
        for variable_name, options in json.load(f)["parameter_space"].items():
            distribution_settings = DistributionParameters(**options).model_dump()
            if "parameters" in distribution_settings:
                check_distribution(
                    result.parameter_space,
                    variable_name,
                    parameters=distribution_settings["parameters"],
                )
            else:
                check_distribution(
                    result.parameter_space,
                    variable_name,
                    **distribution_settings,
                )


def test_write(tmp_wd):
    """Check that a space analysis node result can be saved in readable file format."""
    file_base_name = "result"
    space_analysis_node = SpaceAnalysisNode()
    center_values = {"x": 0.5}
    space_analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values=center_values,
        cov=0.05,
    )
    SpaceAnalysisNodeFileIO().write(
        space_analysis_node.result, file_base_name=file_base_name
    )

    with open(f"{file_base_name}.json") as f:
        settings_dict = json.load(f)["parameter_space"]["x"]
        distribution_parameters = DistributionParameters(**settings_dict)
        assert distribution_parameters.name == "Triangular"
        assert distribution_parameters.mode == 0.5  # ruff: ignore[float-equality-comparison]
        assert distribution_parameters.lower == 0.475  # ruff: ignore[float-equality-comparison]
        assert distribution_parameters.upper == 0.525  # ruff: ignore[float-equality-comparison]
        # An untruncated distribution carries no truncation bounds.
        assert "lower_bound" not in settings_dict
        assert "upper_bound" not in settings_dict


def test_write_for_interfaced_distribution(tmp_wd):
    """Check that a space analysis node result containing an ``InterfacedDistribution`` can be
    saved in readable file format."""
    parameter_space = ParameterSpace()
    add_random_variable_interface(
        parameter_space,
        "x",
        settings=InterfacedDistributionSettings(name="Normal", parameters=(1.0, 0.05)),
    )
    file_base_name = "result"
    SpaceAnalysisNodeFileIO().write(
        SpaceAnalysisNodeResult(parameter_space=parameter_space),
        file_base_name=file_base_name,
    )

    read_parameter_space = (
        SpaceAnalysisNodeFileIO()
        .read(file_name=f"{file_base_name}.json")
        .parameter_space
    )
    marginal = read_parameter_space.distributions["x"].marginals[0]
    assert marginal.vimseo_settings.name == "Normal"
    assert marginal.mean == 1.0  # ruff: ignore[float-equality-comparison]
    assert marginal.standard_deviation == 0.05  # ruff: ignore[float-equality-comparison]


def test_write_with_truncation(tmp_wd):
    """A truncated distribution keeps its ``lower_bound``/``upper_bound`` on write + read.

    Regression: ``_serialize_distribution_parameters`` only emitted the keys in
    ``OPTIONS_PER_DISTRIBUTION`` (``mu``/``sigma`` for a normal), so the truncation
    bounds were silently dropped on write and the distribution was reloaded
    untruncated. The sibling gap on the vector *build* path is covered by
    ``test_space_builders.test_update_vector_from_model_center_and_cov_with_truncation``.
    """
    file_base_name = "result"
    space_analysis_node = SpaceAnalysisNode()
    space_analysis_node.execute(
        distribution_name="OTNormalDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 1.0},
        cov=0.05,
        lower_bounds={"x": 0.9},
        upper_bounds={"x": 1.1},
    )
    SpaceAnalysisNodeFileIO().write(
        space_analysis_node.result, file_base_name=file_base_name
    )

    with open(f"{file_base_name}.json") as f:
        settings_dict = json.load(f)["parameter_space"]["x"]
    assert settings_dict["lower_bound"] == 0.9  # ruff: ignore[float-equality-comparison]
    assert settings_dict["upper_bound"] == 1.1  # ruff: ignore[float-equality-comparison]

    read_parameter_space = (
        SpaceAnalysisNodeFileIO()
        .read(file_name=f"{file_base_name}.json")
        .parameter_space
    )
    check_distribution(
        read_parameter_space,
        "x",
        mu=1.0,
        sigma=0.05,
        lower_bound=0.9,
        upper_bound=1.1,
    )


def test_write_vector_with_truncation(tmp_wd):
    """A truncated *vector* distribution round-trips its per-component bounds.

    Exercises the ``dimension > 1`` branch of the serializer: the bounds must come
    back as one value per component, and rebuild a truncated distribution on read.
    """
    file_base_name = "result"
    space_analysis_node = SpaceAnalysisNode()
    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    variable_name = "x3"  # a size-3 vector input
    model_lower = array([0.98, 1.0, 2.90])
    model_upper = array([1.02, 2.2, 3.10])
    model.lower_bounds[variable_name] = model_lower
    model.upper_bounds[variable_name] = model_upper
    space_analysis_node.execute(
        distribution_name="OTNormalDistribution",
        space_builder_name="FromModelCenterAndCov",
        model=model,
        variable_names=[variable_name],
        use_default_values_as_center=True,
        cov=0.05,
        truncate_to_model_bounds=True,
    )
    SpaceAnalysisNodeFileIO().write(
        space_analysis_node.result, file_base_name=file_base_name
    )

    with open(f"{file_base_name}.json") as f:
        settings_dict = json.load(f)["parameter_space"][variable_name]
    assert settings_dict["lower_bound"] == model_lower.tolist()
    assert settings_dict["upper_bound"] == model_upper.tolist()

    read_parameter_space = (
        SpaceAnalysisNodeFileIO()
        .read(file_name=f"{file_base_name}.json")
        .parameter_space
    )
    check_distribution(
        read_parameter_space,
        variable_name,
        lower_bound=model_lower,
        upper_bound=model_upper,
    )
