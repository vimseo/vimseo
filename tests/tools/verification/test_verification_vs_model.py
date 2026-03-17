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
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import atleast_1d
from numpy import full
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc2_overall_function,
)
from vimseo.tools.verification.verification_vs_model import CodeVerificationAgainstModel
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import generate_dataset

BIAS = 0.5
X1_2_VALUE = 1.0


@pytest.fixture
def reference_data():
    """Create a reference IOdataset based on :class:`.MockModel`. The input-output
    relationship corresponds to MockModel with an added bias.

    Also write the data to a csv file.
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
    return generate_dataset(group_names_to_vars, 3)


@pytest.mark.parametrize("group_name", [IODataset.INPUT_GROUP, Dataset.DEFAULT_GROUP])
def test_verification_against_model(tmp_wd, reference_data, group_name):
    """Check 'simulated versus reference' results from
    :class:`.CodeVerificationAgainstModel` tool using as input a dataset or a csv file.

    Metrics is already checked in ``test_verification_against_data()``.
    """
    # Change group name from "inputs" to "parameters" to check if a ``Dataset`` (whose
    # default group name is "parameters") can be used as input.
    if group_name == Dataset.DEFAULT_GROUP:
        reference_data.rename_group(IODataset.INPUT_GROUP, Dataset.DEFAULT_GROUP)
    verificator = CodeVerificationAgainstModel(
        directory_naming_method=DirectoryNamingMethod.NUMBERED
    )

    model = create_model("MockModel", "LC2")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.cache = None
    model_2 = create_model("MockModel", "LC2")
    # Change default value such that 'model2' returns an output 'y1' different from
    # 'model'.
    model_2.default_input_data["x1_2"] = atleast_1d(X1_2_VALUE)

    verificator.execute(
        model=model, reference_model=model_2, input_dataset=reference_data
    )
    verificator.save_results()

    nb_samples = reference_data.shape[0]
    result = verificator.result

    # All model outputs must be in output variables of the simulation_and_reference
    # dataset.
    assert set(
        result.simulation_and_reference.get_variable_names(
            group_name=IODataset.OUTPUT_GROUP
        )
    ) == {MetaDataNames.cpu_time, "y1_2", "Ref[y1]", "Ref[y1_2]", "y1"}

    assert_array_equal(
        result.simulation_and_reference
        .get_view(variable_names="y1")
        .to_numpy()
        .ravel(),
        full((nb_samples), mock_model_lc2_overall_function(1.0, 0.0)[0]),
    )
    assert_array_equal(
        result.simulation_and_reference
        .get_view(variable_names="Ref[y1]")
        .to_numpy()
        .ravel(),
        full((nb_samples), mock_model_lc2_overall_function(1.0, X1_2_VALUE)[0]),
    )


def test_verification_against_model_with_output_names_restriction(
    tmp_wd, reference_data
):
    """Check that verifying a model containing less output variables than the reference
    model can be done by restraining the verified output variables with arg
    output_names."""
    verificator = CodeVerificationAgainstModel()

    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.cache = None
    model_2 = create_model("MockModel", "LC2")
    # Change default value such that 'model2' returns an output 'y1' different from
    # 'model'.
    model_2.default_input_data["x1_2"] = atleast_1d(X1_2_VALUE)

    verificator.execute(
        model=model,
        reference_model=model_2,
        input_dataset=reference_data,
        output_names=["y1"],
    )

    assert set(
        verificator.result.simulation_and_reference.get_variable_names(
            group_name=IODataset.OUTPUT_GROUP
        )
    ) == {"y1", MetaDataNames.cpu_time, "Ref[y1]"}
