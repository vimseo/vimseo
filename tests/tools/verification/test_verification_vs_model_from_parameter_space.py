# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset
from numpy import atleast_1d
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc2_overall_function,
)
from vimseo.tools.verification.verification_vs_model_from_parameter_space import (
    CodeVerificationAgainstModelFromParameterSpace,
)

BIAS = 0.5
X1_2_VALUE = 1.0


@pytest.fixture
def parameter_space():
    """Create a space of parameters with scalar variable ``x1`` uniformly distributed
    over [-1, 1]."""
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, lower=-1.0, upper=1.0
    )
    return parameter_space


def test_verification_against_model_from_space_tool_result(tmp_wd, parameter_space):
    """Check 'simulated versus reference' results from
    :class:`.CodeVerificationAgainstModelFromParameterSpace` tool using as input a
    parameter space and running a DOE."""
    nb_samples = 10
    verificator = CodeVerificationAgainstModelFromParameterSpace()

    model = create_model("MockModel", "LC2")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.cache = None
    model_2 = create_model("MockModel", "LC2")
    # Change default value such that 'model2' returns an output 'y1' different from
    # 'model'.
    model_2.default_input_data["x1_2"] = atleast_1d(X1_2_VALUE)

    verificator.execute(
        model=model,
        reference_model=model_2,
        parameter_space=parameter_space,
        output_names=["y1"],
        n_samples=nb_samples,
    )
    result = verificator.result

    # All model outputs must be in output variables of the simulation_and_reference
    # dataset.
    assert set(
        result.simulation_and_reference.get_variable_names(
            group_name=IODataset.OUTPUT_GROUP
        )
    ) == {MetaDataNames.cpu_time, "y1", "Ref[y1]"}

    assert_array_equal(
        result.simulation_and_reference
        .get_view(variable_names="y1")
        .to_numpy()
        .ravel(),
        mock_model_lc2_overall_function(
            result.simulation_and_reference
            .get_view(variable_names="x1")
            .to_numpy()
            .ravel(),
            0.0,
        )[0],
    )
    assert_array_equal(
        result.simulation_and_reference
        .get_view(variable_names="Ref[y1]")
        .to_numpy()
        .ravel(),
        mock_model_lc2_overall_function(
            result.simulation_and_reference
            .get_view(variable_names="x1")
            .to_numpy()
            .ravel(),
            X1_2_VALUE,
        )[0],
    )
