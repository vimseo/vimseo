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

"""Check that the tools accept plain mappings and DataFrames, and that doing so gives
the same results as passing a fully grouped dataset."""

from __future__ import annotations

import pytest
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from numpy.testing import assert_allclose
from pandas import DataFrame

from vimseo.api import create_model
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.statistics.statistics_tool import StatisticsTool
from vimseo.tools.validation_case.validation_case import DeterministicValidationCase
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseInputs,
)
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseSettings,
)
from vimseo.tools.verification.solution_verification import (
    DiscretizationSolutionVerification,
)
from vimseo.tools.verification.verification_vs_data import CodeVerificationAgainstData

pytestmark = pytest.mark.fast

CONVERGENCE_DATA = {
    "dx": [1.0, 0.5, 0.25, 0.125],
    "q": [3.0, 3.5, 3.75, 3.875],
}


@pytest.fixture
def convergence_dataset():
    """The convergence data as a fully grouped dataset."""
    return IODataset.from_array(
        array([CONVERGENCE_DATA["dx"], CONVERGENCE_DATA["q"]]).T,
        variable_names=["dx", "q"],
        variable_names_to_group_names={
            "dx": IODataset.INPUT_GROUP,
            "q": IODataset.OUTPUT_GROUP,
        },
    )


@pytest.mark.parametrize(
    "simulated_data",
    [
        CONVERGENCE_DATA,
        DataFrame(CONVERGENCE_DATA),
        {
            "inputs": {"dx": CONVERGENCE_DATA["dx"]},
            "outputs": {"q": CONVERGENCE_DATA["q"]},
        },
    ],
    ids=["mapping", "dataframe", "nested_mapping"],
)
def test_solution_verification_accepts_plain_data(
    tmp_wd, convergence_dataset, simulated_data
):
    """Check that the solution verification gives the same result whatever the form of
    the simulated data."""
    expected = (
        DiscretizationSolutionVerification()
        .execute(
            simulated_data=convergence_dataset,
            element_size_variable_name="dx",
            abscissa_name="dx",
            output_name="q",
        )
        .extrapolation
    )

    extrapolation = (
        DiscretizationSolutionVerification()
        .execute(
            simulated_data=simulated_data,
            element_size_variable_name="dx",
            abscissa_name="dx",
            output_name="q",
        )
        .extrapolation
    )

    assert_allclose(extrapolation["q_converged"], expected["q_converged"])
    assert_allclose(extrapolation["order_fit"], expected["order_fit"])


def test_statistics_accepts_a_mapping(tmp_wd):
    """Check that the statistics tool accepts a mapping."""
    samples = [1.0, 1.4, 2.2, 2.9, 3.1, 3.8, 4.4, 5.1]

    expected = StatisticsTool().execute(
        dataset=IODataset.from_array(array([samples]).T, variable_names=["e"]),
        tested_distributions=["Normal"],
    )
    result = StatisticsTool().execute(
        dataset={"e": samples}, tested_distributions=["Normal"]
    )

    assert_allclose(result.statistics["mean"]["e"], expected.statistics["mean"]["e"])
    assert_allclose(
        result.statistics["variance"]["e"], expected.statistics["variance"]["e"]
    )


def test_custom_doe_accepts_a_mapping(tmp_wd):
    """Check that the custom DOE resolves its input group from the model."""
    model = create_model("MockModel", "LC1")

    result = CustomDOETool().execute(
        model=model, input_dataset={"x1": [0.2, 0.5, 1.0]}, output_names=["y1"]
    )

    assert result.dataset.shape[0] == 3
    assert "x1" in result.dataset.get_variable_names(IODataset.INPUT_GROUP)


def test_verification_vs_data_accepts_a_mapping(tmp_wd):
    """Check that the roles of the reference data are read from the model grammars."""
    model = create_model("MockModel", "LC1")
    reference_data = {"x1": [0.2, 0.5, 1.0], "y1": [2.0, 3.0, 4.0]}

    verificator = CodeVerificationAgainstData()
    verificator.execute(model=model, reference_data=reference_data)

    dataset = verificator.result.simulation_and_reference
    assert "y1" in dataset.get_variable_names(group_name="Reference")
    assert_allclose(
        dataset
        .get_view(group_names="Reference", variable_names="y1")
        .to_numpy()
        .ravel(),
        reference_data["y1"],
    )


def test_validation_case_accepts_ragged_vectors(tmp_wd):
    """Check that a mapping holding vectors of different lengths is accepted, and that
    it matches the csv-based reference data of the same model."""
    model = create_model("MockModelPersistent", "LC1")
    reference_data = {
        "x1": [1.0, 2.0],
        "x2": [6.0, 7.0],
        "x3": [array([1.0, 2.0]), array([3.0, 4.0, 5.0])],
        "y4": [3.3, 14.4],
    }

    validation = DeterministicValidationCase()
    validation.execute(
        inputs=DeterministicValidationCaseInputs(
            model=model, reference_data=reference_data
        ),
        settings=DeterministicValidationCaseSettings(output_names=["y4"]),
    )

    metrics = validation.result.element_wise_metrics
    assert metrics.shape[0] == 2
    assert "x3" in metrics.get_variable_names(IODataset.INPUT_GROUP)
    assert metrics.variable_names_to_n_components["x3"] == 3
