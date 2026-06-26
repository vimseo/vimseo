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
from gemseo.datasets.io_dataset import IODataset
from gemseo.mlearning.regression.algos.linreg import LinearRegressor
from numpy import array
from numpy.testing import assert_allclose

from vimseo.api import create_model
from vimseo.problems.beam_analytic.reference_dataset_builder import (
    bending_test_analytical_reference_dataset,
)
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.surrogate.surrogate import LEARN
from vimseo.tools.surrogate.surrogate import LOO
from vimseo.tools.surrogate.surrogate import SurrogateTool
from vimseo.tools.surrogate.surrogate_result import SurrogateResult
from vimseo.utilities.datasets import DatasetAddFromModel

EXPECTED_PATTERNS_IN_RESULTS = [
    "Surrogate model: MockModel.LC1.LinearRegressor",
    "Summary of Surrogate Quality",
]
SELECTION_QUALITITES_TITLE = "Qualities of all candidate algorithms"


@pytest.fixture
def mock_dataset():
    """Create a toy dataset."""
    dataset = IODataset()
    dataset.add_variable(
        variable_name="x1",
        data=array([[-1.0], [0.0], [1.0], [2.0], [3.0]]),
        group_name=IODataset.INPUT_GROUP,
    )
    dataset.add_variable(
        variable_name="y1",
        data=array([[3.0], [5.0], [7.0], [9.0], [11.0]]),
        group_name=IODataset.OUTPUT_GROUP,
    )
    return dataset


@pytest.fixture
def bending_test_analytical_dataset():
    """The reference dataset representing the Cantiliver load case of the
    BendingTestAnalytical."""
    return bending_test_analytical_reference_dataset()["Cantilever"]


@pytest.fixture
def mock_model_surrogate(mock_dataset):
    """Construct and execute the ``SurrogateTool`` on ``MockModel`` model."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    surrogate_tool = SurrogateTool()
    # remove PolynomialRegressor candidate since it has same quality as LinearRegressor
    # and the choice between the two is not deterministic.
    candidates = surrogate_tool.options["candidates"]
    for i, candidate in enumerate(candidates):
        if candidate[0] == "PolynomialRegressor":
            del candidates[i]  # noqa: B909
    surrogate_tool.execute(
        model=model,
        dataset=mock_dataset,
        quality_for_selection=("MSEMeasure", LOO),
        evaluation_methods=[LOO, LEARN],
    )
    surrogate_tool.save_results()
    return surrogate_tool


@pytest.fixture
def bending_test_analytical_surrogate(bending_test_analytical_dataset):
    """Construct and execute the ``SurrogateTool`` on ``BendingTestAnalyticalDataset``
    model."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    surrogate_tool = SurrogateTool()
    surrogate_tool.execute(
        model=model,
        dataset=bending_test_analytical_dataset,
        output_names=["reaction_forces", "dplt_at_force_location"],
        quality_for_selection=("MSEMeasure", LOO),
        evaluation_methods=[LOO, LEARN],
    )
    surrogate_tool.save_results()
    return surrogate_tool


# TODO kfolds method creates an error
@pytest.mark.parametrize(
    "eval_methods",
    [[LOO, LEARN]],
)
def test_mockmodel_surrogate(tmp_wd, mock_dataset, eval_methods):
    """Check that a user-defined surrogate algorithm correctly fits the dataset, with an
    error close to zero."""

    model = MockModel("LC1")
    algo = "LinearRegressor"
    surrogate_tool = SurrogateTool()
    surrogate_tool.update_options(evaluation_methods=eval_methods)
    results = surrogate_tool.execute(model=model, dataset=mock_dataset, algo=algo)

    for m in eval_methods:
        assert results.qualities["MSEMeasure"][m] == pytest.approx(0, abs=1e-20)


def test_mock_model_surrogate_selection(tmp_wd, mock_dataset):
    """Use default candidate algorithms for selection of the best surrogate model
    according to specific quality measure and evaluation method for selection."""
    model = MockModel("LC1")
    surrogate_tool = SurrogateTool()
    surrogate_tool.execute(
        model=model,
        dataset=mock_dataset,
        quality_for_selection=("MSEMeasure", LOO),
        evaluation_methods=[LOO, LEARN],
    )
    assert isinstance(surrogate_tool.selected_algo, LinearRegressor)


def test_adding_candidate_algo(tmp_wd):
    """Check that a candidate is correctly added."""
    surrogate_tool = SurrogateTool()
    candidate_name = "PolynomialRegressor"
    new_candidate = {
        candidate_name: {"degree": [4, 5], "fit_intercept": [True, False]},
    }
    surrogate_tool.add_candidate(new_candidate)

    assert candidate_name in surrogate_tool.options["candidates"]
    assert (
        surrogate_tool.options["candidates"][candidate_name]
        == new_candidate[candidate_name]
    )


def test_surrogate_mock_model(tmp_wd, mock_model_surrogate):
    """Check that a surrogate analysis on ``MockModel`` (linear model) fits perfectly,
    and check that the ``PredictionVsTrue`` is generated."""
    results = mock_model_surrogate.result

    prediction = results.model.execute({"x1": array([0.5])})
    assert prediction["y1"][0] == pytest.approx(6.0)

    assert results.qualities["MSEMeasure"][LEARN][0] == pytest.approx(0)
    assert results.qualities["MSEMeasure"][LOO][0] == pytest.approx(0)


def test_surrogate_bending_test_analytical(
    tmp_wd, bending_test_analytical_dataset, bending_test_analytical_surrogate
):
    """Check that a surrogate analysis on ``BendingTestAnalytical`` (Polynomial model)
    fits perfectly the reference dataset."""
    surrogate_tool = bending_test_analytical_surrogate
    dataset = bending_test_analytical_dataset

    output_name = "reaction_forces"
    # TODO following line generates an error in GEMSEO:
    #  > if algo_name not in self.descriptions:
    #      E
    #      TypeError: unhashable
    #      type: 'IODataset'
    #  / home / sebastien.bocquet / PycharmProjects / vims_only /.tox / py311 / lib / python3
    #  .11 / site - packages / gemseo / algos / algorithm_library.py: 375: TypeError
    # dataset = CustomDOE().execute(surrogate_tool.result.model, input_dataset).dataset
    DatasetAddFromModel.add_group(
        dataset=dataset,
        input_group_name=IODataset.INPUT_GROUP,
        input_variable_names=dataset.get_variable_names(
            group_name=IODataset.INPUT_GROUP
        ),
        model=surrogate_tool.result.model,
        output_group_name="from_surrogate",
        output_variable_name=output_name,
        bias=0.0,
    )
    assert_allclose(
        dataset.to_dict_of_arrays(by_group=True)[IODataset.OUTPUT_GROUP][output_name],
        dataset.to_dict_of_arrays(by_group=True)["from_surrogate"][output_name],
    )

    assert surrogate_tool.result.qualities["MSEMeasure"][LEARN][0] == pytest.approx(0)
    # This value is around 9. To be inverstigated if OK.
    # assert surrogate_tool.result.qualities["MSEMeasure"][LOO][0] == pytest.approx(0)


def test_load_and_plot_mock_model(tmp_wd, mock_model_surrogate):
    """Check that a surrogate result can be loaded from disk and that a
    ``PredictionVsTrue`` plot can be created."""
    results = BaseTool.load_results(
        mock_model_surrogate.working_directory / "SurrogateTool_result.hdf5"
    )
    mock_model_surrogate.plot_results(results, save=True, show=False)
    assert Path("surrogate_LinReg_MockModel.LC1.png").is_file()


def test_show_results_after_selection(tmp_wd, mock_dataset):
    """Check results representation when algo selection is used."""
    model = MockModel("LC1")
    quality_measures = ["MSEMeasure", "RMSEMeasure"]
    evaluation_methods = [LOO, LEARN]
    surrogate_tool = SurrogateTool()

    # remove PolynomialRegressor candidate since it has same quality as LinearRegressor
    # and the choice between the two is not deterministic.
    candidates = surrogate_tool.options["candidates"]
    for i, candidate in enumerate(candidates):
        if candidate[0] == "PolynomialRegressor":
            del candidates[i]  # noqa: B909

    surrogate_tool.execute(
        model=model,
        dataset=mock_dataset,
        quality_for_selection=("MSEMeasure", LOO),
        quality_measures=quality_measures,
        evaluation_methods=evaluation_methods,
    )

    msg = str(surrogate_tool.result)

    expected_patterns = EXPECTED_PATTERNS_IN_RESULTS
    expected_patterns.extend(quality_measures)
    expected_patterns.extend(evaluation_methods)
    for pattern in expected_patterns:
        assert pattern in msg

    assert SELECTION_QUALITITES_TITLE in msg


def test_show_results_no_selection(tmp_wd, mock_dataset):
    """Check results representation without algo selection."""
    model = MockModel("LC1")
    evaluation_methods = [LOO, LEARN]
    surrogate_tool = SurrogateTool()
    surrogate_tool.execute(
        model=model,
        dataset=mock_dataset,
        algo="LinearRegressor",
        evaluation_methods=evaluation_methods,
    )

    msg = str(surrogate_tool.result)

    expected_patterns = EXPECTED_PATTERNS_IN_RESULTS
    expected_patterns.extend("MSEMeasure")
    expected_patterns.extend(evaluation_methods)

    assert SELECTION_QUALITITES_TITLE not in msg


def test_serialization(tmp_wd, mock_dataset):
    """Check that a SurrogateToolResult can be serialized to hdf5."""
    model = MockModel("LC1")
    evaluation_methods = [LOO, LEARN]
    surrogate_tool = SurrogateTool()
    surrogate_tool.execute(
        model=model,
        dataset=mock_dataset,
        algo="LinearRegressor",
        evaluation_methods=evaluation_methods,
    )
    result = surrogate_tool.result
    result.to_hdf5("result.hdf5")
    serialized_result = SurrogateResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)
