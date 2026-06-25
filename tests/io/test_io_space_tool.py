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
from gemseo.uncertainty.distributions.base_distribution import (
    InterfacedDistributionSettings,
)

from vimseo.io.space_io import SpaceToolFileIO
from vimseo.io.test_data import IO_DATA_DIR
from vimseo.tools.space.random_variable_interface import add_random_variable_interface
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.tools.space.space_tool_result import SpaceToolResult
from vimseo.utilities.distribution import DistributionParameters
from vimseo.utilities.distribution_utils import check_distribution


@pytest.mark.parametrize("as_byte", [True, False])
@pytest.mark.parametrize(
    "from_buffer",
    [True, False],
)
def test_read(from_buffer, as_byte):
    """Check that a space tool result can be instantiated from a readable result file."""
    file_path = IO_DATA_DIR / "space_tool" / "space_tool_result.json"

    if from_buffer:
        mode = "rb" if as_byte else "r"
        with open(file_path, mode) as f:
            result = SpaceToolFileIO().read_buffer(f.read())
    else:
        result = SpaceToolFileIO().read(file_path)

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
    """Check that a space tool result can be saved in readable file format."""
    file_base_name = "result"
    space_tool = SpaceTool()
    center_values = {"x": 0.5}
    space_tool.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values=center_values,
        cov=0.05,
    )
    SpaceToolFileIO().write(space_tool.result, file_base_name=file_base_name)

    with open(f"{file_base_name}.json") as f:
        settings_dict = json.load(f)["parameter_space"]["x"]
        distribution_parameters = DistributionParameters(**settings_dict)
        assert distribution_parameters.name == "Triangular"
        assert distribution_parameters.mode == 0.5
        assert distribution_parameters.lower == 0.475
        assert distribution_parameters.upper == 0.525


def test_write_for_interfaced_distribution(tmp_wd):
    """Check that a space tool result containing an ``InterfacedDistribution`` can be
    saved in readable file format."""
    parameter_space = ParameterSpace()
    add_random_variable_interface(
        parameter_space,
        "x",
        settings=InterfacedDistributionSettings(name="Normal", parameters=(1.0, 0.05)),
    )
    file_base_name = "result"
    SpaceToolFileIO().write(
        SpaceToolResult(parameter_space=parameter_space), file_base_name=file_base_name
    )

    read_parameter_space = (
        SpaceToolFileIO().read(file_name=f"{file_base_name}.json").parameter_space
    )
    marginal = read_parameter_space.distributions["x"].marginals[0]
    assert marginal.settings["name"] == "Normal"
    assert marginal.mean == 1.0
    assert marginal.standard_deviation == 0.05
