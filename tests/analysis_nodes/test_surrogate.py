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
from gemseo.datasets.io_dataset import IODataset
from gemseo.mlearning.regression.algos.linreg import LinearRegressor
from numpy import array
from numpy.testing import assert_allclose

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_result import assert_results_equal
from vimseo.analysis_nodes.surrogate.surrogate import LEARN
from vimseo.analysis_nodes.surrogate.surrogate import LOO
from vimseo.analysis_nodes.surrogate.surrogate import SurrogateAnalysisNode
from vimseo.analysis_nodes.surrogate.surrogate_result import SurrogateResult
from vimseo.api import create_model
from vimseo.problems.beam_analytic.reference_dataset_builder import (
    bending_test_analytical_reference_dataset,
)
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.utilities.datasets import DatasetAddFromModel
from vimseo.utilities.test_utils import check_result_visualization

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
    """Construct and execute the ``SurrogateAnalysisNode`` on ``MockModel`` model."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    surrogate_analysis_node = SurrogateAnalysisNode()
    # remove PolynomialRegressor candidate since it has same quality as LinearRegressor
    # and the choice between the two is not deterministic.
    candidates = surrogate_analysis_node.options["candidates"]
    for i, candidate in enumerate(candidates):
        if candidate[0] == "PolynomialRegressor":
            del candidates[i]  # ruff: ignore[loop-iterator-mutation]
    surrogate_analysis_node.execute(
        model=model,
        dataset=mock_dataset,
        quality_for_selection=("MSEMeasure", LOO),
        evaluation_methods=[LOO, LEARN],
    )
    surrogate_analysis_node.save_results()
    return surrogate_analysis_node


@pytest.fixture
def bending_test_analytical_surrogate(bending_test_analytical_dataset):
    """Construct and execute the ``SurrogateAnalysisNode`` on ``BendingTestAnalyticalDataset``
    model."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    surrogate_analysis_node = SurrogateAnalysisNode()
    surrogate_analysis_node.execute(
        model=model,
        dataset=bending_test_analytical_dataset,
        output_names=["reaction_forces", "dplt_at_force_location"],
        quality_for_selection=("MSEMeasure", LOO),
        evaluation_methods=[LOO, LEARN],
    )
    surrogate_analysis_node.save_results()
    return surrogate_analysis_node


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
    surrogate_analysis_node = SurrogateAnalysisNode()
    surrogate_analysis_node.update_options(evaluation_methods=eval_methods)
    results = surrogate_analysis_node.execute(
        model=model, dataset=mock_dataset, algo=algo
    )

    for m in eval_methods:
        assert results.qualities["MSEMeasure"][m] == pytest.approx(0, abs=1e-20)


def test_mock_model_surrogate_selection(tmp_wd, mock_dataset):
    """Use default candidate algorithms for selection of the best surrogate model
    according to specific quality measure and evaluation method for selection."""
    model = MockModel("LC1")
    surrogate_analysis_node = SurrogateAnalysisNode()
    surrogate_analysis_node.execute(
        model=model,
        dataset=mock_dataset,
        quality_for_selection=("MSEMeasure", LOO),
        evaluation_methods=[LOO, LEARN],
    )
    assert isinstance(surrogate_analysis_node.selected_algo, LinearRegressor)


def test_adding_candidate_algo(tmp_wd):
    """Check that a candidate is correctly added."""
    surrogate_analysis_node = SurrogateAnalysisNode()
    candidate_name = "PolynomialRegressor"
    new_candidate = {
        candidate_name: {"degree": [4, 5], "fit_intercept": [True, False]},
    }
    surrogate_analysis_node.add_candidate(new_candidate)

    assert candidate_name in surrogate_analysis_node.options["candidates"]
    assert (
        surrogate_analysis_node.options["candidates"][candidate_name]
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
    surrogate_analysis_node = bending_test_analytical_surrogate
    dataset = bending_test_analytical_dataset

    output_name = "reaction_forces"
    # TODO following line generates an error in GEMSEO:
    #  > if algo_name not in self.descriptions:
    #      E
    #      TypeError: unhashable
    #      type: 'IODataset'  # ruff: ignore[legacy-type-comment]
    #  / home / sebastien.bocquet / PycharmProjects / vims_only /.tox / py311 / lib / python3
    #  .11 / site - packages / gemseo / algos / algorithm_library.py: 375: TypeError
    # dataset = CustomDOE().execute(surrogate_analysis_node.result.model, input_dataset).dataset
    DatasetAddFromModel.add_group(
        dataset=dataset,
        input_group_name=IODataset.INPUT_GROUP,
        input_variable_names=dataset.get_variable_names(
            group_name=IODataset.INPUT_GROUP
        ),
        model=surrogate_analysis_node.result.model,
        output_group_name="from_surrogate",
        output_variable_name=output_name,
        bias=0.0,
    )
    assert_allclose(
        dataset.to_dict_of_arrays(by_group=True)[IODataset.OUTPUT_GROUP][output_name],
        dataset.to_dict_of_arrays(by_group=True)["from_surrogate"][output_name],
    )

    assert surrogate_analysis_node.result.qualities["MSEMeasure"][LEARN][
        0
    ] == pytest.approx(0)
    # This value is around 9. To be inverstigated if OK.
    # assert surrogate_analysis_node.result.qualities["MSEMeasure"][LOO][0] == pytest.approx(0)


def test_load_and_plot_mock_model(tmp_wd, mock_model_surrogate):
    """Check that a surrogate result can be loaded from disk and that a
    ``PredictionVsTrue`` plot can be created."""
    results = BaseAnalysisNode.load_results(
        mock_model_surrogate.working_directory / "SurrogateAnalysisNode_result.hdf5"
    )
    results.plot(directory_path=mock_model_surrogate.working_directory, save=True)
    assert list(mock_model_surrogate.working_directory.glob("surrogate_*.png"))


def test_plot_without_save_writes_no_file(tmp_wd, mock_model_surrogate):
    """With ``save=False`` (the default), no figure is written to disk."""
    results = BaseAnalysisNode.load_results(
        mock_model_surrogate.working_directory / "SurrogateAnalysisNode_result.hdf5"
    )
    results.plot(directory_path=mock_model_surrogate.working_directory)
    assert not list(mock_model_surrogate.working_directory.glob("surrogate_*.png"))


def test_show_results_after_selection(tmp_wd, mock_dataset):
    """Check results representation when algo selection is used."""
    model = MockModel("LC1")
    quality_measures = ["MSEMeasure", "RMSEMeasure"]
    evaluation_methods = [LOO, LEARN]
    surrogate_analysis_node = SurrogateAnalysisNode()

    # remove PolynomialRegressor candidate since it has same quality as LinearRegressor
    # and the choice between the two is not deterministic.
    candidates = surrogate_analysis_node.options["candidates"]
    for i, candidate in enumerate(candidates):
        if candidate[0] == "PolynomialRegressor":
            del candidates[i]  # ruff: ignore[loop-iterator-mutation]

    surrogate_analysis_node.execute(
        model=model,
        dataset=mock_dataset,
        quality_for_selection=("MSEMeasure", LOO),
        quality_measures=quality_measures,
        evaluation_methods=evaluation_methods,
    )

    msg = str(surrogate_analysis_node.result)

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
    surrogate_analysis_node = SurrogateAnalysisNode()
    surrogate_analysis_node.execute(
        model=model,
        dataset=mock_dataset,
        algo="LinearRegressor",
        evaluation_methods=evaluation_methods,
    )

    msg = str(surrogate_analysis_node.result)

    expected_patterns = EXPECTED_PATTERNS_IN_RESULTS
    expected_patterns.extend("MSEMeasure")
    expected_patterns.extend(evaluation_methods)

    assert SELECTION_QUALITITES_TITLE not in msg


def test_serialization(tmp_wd, mock_dataset):
    """Check that a SurrogateAnalysisNodeResult can be serialized to hdf5."""
    model = MockModel("LC1")
    evaluation_methods = [LOO, LEARN]
    surrogate_analysis_node = SurrogateAnalysisNode()
    surrogate_analysis_node.execute(
        model=model,
        dataset=mock_dataset,
        algo="LinearRegressor",
        evaluation_methods=evaluation_methods,
    )
    result = surrogate_analysis_node.result
    result.to_hdf5("result.hdf5")
    serialized_result = SurrogateResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)


def test_result_visualization(tmp_wd, mock_model_surrogate):
    """Check that a surrogate result can be visualized once loaded from a file."""
    check_result_visualization(mock_model_surrogate.result, "visualization")
    tables = mock_model_surrogate.result.to_dataframes()
    assert "MSEMeasure" in tables["qualities"].index
    assert "selection_qualities" in tables
