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
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import full
from numpy import vstack
from numpy.testing import assert_array_equal

from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc2_overall_function,
)
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.doe.doe_result import DOEResult
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import generate_dataset

N_SAMPLES = 5


@pytest.fixture
def parameter_space():
    """Create a space of parameters with scalar variable ``x1`` uniformly distributed
    over [-1, 1]."""
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, lower=-1.0, upper=1.0
    )
    return parameter_space


@pytest.fixture
def input_dataset():
    """Create a dataset with a group named ``IODataset.INPUT_GROUP`` containing three
    samples of variables ``x1`` and ``x1_2``, each equal to 1."""
    return generate_dataset(
        {
            IODataset.INPUT_GROUP: [
                Variable("x1", 1.0, is_constant_value=True),
                Variable("x1_2", 1.0, is_constant_value=True),
            ],
        },
        3,
    )


@pytest.fixture
def mock_model_doe(parameter_space):
    model = MockModel("LC1")
    doe_tool = DOETool()
    output_names = ["y1"]
    doe_tool.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=output_names,
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )
    return doe_tool


@pytest.mark.parametrize(
    ("input_names", "output_names"),
    [
        ((), ()),
        (["x1"], ()),
        ((), ["y1"]),
    ],
)
def test_custom_doe(tmp_wd, input_dataset, input_names, output_names):
    """Check :class:`.CustomDOETool` in case of specific ``input_names`` or not, and
    specific ``output_names`` or not."""

    model = MockModel("LC2")
    doe_tool = CustomDOETool()

    dataset = doe_tool.execute(
        model=model,
        input_dataset=input_dataset,
        input_names=input_names,
        output_names=output_names,
    ).dataset

    nb_samples = input_dataset.shape[0]
    expected_output = (
        Dataset()
        .from_array(
            data=vstack([
                mock_model_lc2_overall_function(
                    input_dataset.get_view(variable_names="x1").to_numpy().flatten(),
                    (
                        full((nb_samples), model.default_input_data["x1_2"][0])
                        if input_names == ["x1"]
                        else input_dataset
                        .get_view(variable_names="x1_2")
                        .to_numpy()
                        .flatten()
                    ),
                )
            ]).T,
            variable_names=["y1", "y1_2"],
            variable_names_to_group_names={
                "y1": IODataset.OUTPUT_GROUP,
                "y1_2": IODataset.OUTPUT_GROUP,
            },
        )
        .get_view(variable_names=output_names)
    )

    assert_array_equal(
        dataset.get_view(group_names=IODataset.INPUT_GROUP).to_numpy(),
        input_dataset.get_view(
            group_names=IODataset.INPUT_GROUP, variable_names=input_names
        ).to_numpy(),
    )
    assert_array_equal(
        dataset.get_view(
            group_names=IODataset.OUTPUT_GROUP,
            variable_names=expected_output.get_variable_names(
                group_name=IODataset.OUTPUT_GROUP
            ),
        ).to_numpy(),
        expected_output.get_view(group_names=IODataset.OUTPUT_GROUP).to_numpy(),
    )


def test_opt_lhs_doe(tmp_wd, mock_model_doe):
    """Check DOE from an OPT_LHS sampling."""

    dataset = mock_model_doe.result.dataset
    dataset_x1 = dataset.get_view(group_names="inputs", variable_names="x1").values
    dataset_y1 = dataset.get_view(group_names="outputs", variable_names="y1").values
    assert len(dataset_x1) == N_SAMPLES
    assert len(dataset_y1) == N_SAMPLES


def test_save_and_load_result(tmp_wd, mock_model_doe):
    """Check that a DOE analysis can be saved and that a new instance can be created and
    loaded from saved data."""
    mock_model_doe.save_results()

    results = BaseTool.load_results(
        mock_model_doe.working_directory / "DOETool_result.hdf5"
    )
    dataset = results.dataset
    dataset_x1 = dataset.get_view(group_names="inputs", variable_names="x1")
    dataset_y1 = dataset.get_view(group_names="outputs", variable_names="y1")
    assert len(dataset_x1) == N_SAMPLES
    assert len(dataset_y1) == N_SAMPLES


def test_serialization(tmp_wd, mock_model_doe):
    """Check that a DOE result can be serialized to hdf5."""
    result = mock_model_doe.result
    result.to_hdf5("result.hdf5")
    serialized_result = DOEResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)
