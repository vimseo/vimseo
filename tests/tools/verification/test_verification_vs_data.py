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
from gemseo.datasets.io_dataset import IODataset
from numpy import full
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc2_overall_function,
)
from vimseo.tools.verification.verification_vs_data import CodeVerificationAgainstData
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import generate_dataset

BIAS = 0.5


@pytest.fixture
def reference_data():
    """Create a reference IOdataset based on :class:`.MockModel`.

    The input-output relationship corresponds to MockModel with an added bias.
    """
    group_names_to_vars = {
        IODataset.INPUT_GROUP: [Variable("x1", 1.0, is_constant_value=True)],
        IODataset.OUTPUT_GROUP: [
            Variable(
                "y1",
                mock_model_lc2_overall_function(1.0, 0.0)[0] + BIAS,
                is_constant_value=True,
            )
        ],
    }
    return IODataset(generate_dataset(group_names_to_vars, 3))


@pytest.fixture
def reference_data_two_output_variables():
    """Create a reference IOdataset based on :class:`.MockModel`, with an additional
    output variable ``y2``."""
    group_names_to_vars = {
        IODataset.INPUT_GROUP: [Variable("x1", 1.0, is_constant_value=True)],
        IODataset.OUTPUT_GROUP: [
            Variable(
                "y1",
                mock_model_lc2_overall_function(1.0, 0.0)[0] + BIAS,
                is_constant_value=True,
            ),
            Variable(
                "y2",
                2.0,
                is_constant_value=True,
            ),
        ],
    }
    return IODataset(generate_dataset(group_names_to_vars, 3))


def test_verification_against_data(tmp_wd, reference_data):
    """Check 'simulated versus reference' and metrics results from
    :class:`.CodeVerificationAgainstData` using as input a dataset or a csv file."""
    verificator = CodeVerificationAgainstData()
    verificator.options["metric_names"] = [
        "SquaredErrorMetric",
        "AbsoluteErrorMetric",
    ]
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    verificator.execute(model=model, reference_data=reference_data)

    nb_samples = reference_data.shape[0]
    result = verificator.result

    assert set(
        result.simulation_and_reference.get_variable_names(
            group_name=IODataset.OUTPUT_GROUP
        )
    ) == {"y1", MetaDataNames.cpu_time.value}
    assert set(
        result.simulation_and_reference.get_variable_names(group_name="Reference")
    ) == {"y1"}

    assert_array_equal(
        result.simulation_and_reference.get_view(
            variable_names="y1", group_names=IODataset.OUTPUT_GROUP
        ).to_numpy()
        + BIAS,
        reference_data.get_view(variable_names="y1").to_numpy(),
    )
    assert_array_equal(
        result.simulation_and_reference.get_view(
            variable_names="y1", group_names="Reference"
        ).to_numpy(),
        reference_data.get_view(variable_names="y1").to_numpy(),
    )

    # Check expected group names in the result dataset
    expected_group_names = verificator.options["metric_names"] + [IODataset.INPUT_GROUP]
    assert set(expected_group_names) == set(result.element_wise_metrics.group_names)

    assert_array_equal(
        result.element_wise_metrics.get_view(variable_names="x1").to_numpy(),
        reference_data.get_view(variable_names="x1").to_numpy(),
    )
    assert_array_equal(
        result.element_wise_metrics
        .get_view(group_names="SquaredErrorMetric", variable_names="y1")
        .to_numpy()
        .ravel(),
        full((nb_samples), BIAS**2),
    )
    assert_array_equal(
        result.element_wise_metrics
        .get_view(
            group_names="AbsoluteErrorMetric",
            variable_names="y1",
        )
        .to_numpy()
        .ravel(),
        full((nb_samples), BIAS),
    )
    assert result.integrated_metrics["SquaredErrorMetric"]["y1"] == pytest.approx(0.25)
    assert result.integrated_metrics["AbsoluteErrorMetric"]["y1"] == pytest.approx(0.5)


def test_verification_against_data_with_output_names_restriction(
    tmp_wd,
    reference_data_two_output_variables,
):
    """Check that verifying a model containing less output variables than the reference
    dataset output group can be done by restraining the verified output variables with
    arg output_names."""
    verificator = CodeVerificationAgainstData()
    model = create_model("MockModel", "LC2")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    verificator.execute(
        model=model,
        reference_data=reference_data_two_output_variables,
        output_names=["y1"],
        metric_names=["SquaredErrorMetric", "AbsoluteErrorMetric"],
    )

    result = verificator.result
    verificator.save_results()

    # All model outputs must be in output variables of the simulation_and_reference
    # dataset.
    assert set(
        result.simulation_and_reference.get_variable_names(
            group_name=IODataset.OUTPUT_GROUP
        )
    ) == {"y1", MetaDataNames.cpu_time.value}
    assert set(
        result.simulation_and_reference.get_variable_names(group_name="Reference")
    ) == {"y1"}
