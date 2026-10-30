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
from numpy import array
from numpy import full
from numpy import vstack
from numpy.testing import assert_allclose
from numpy.testing import assert_array_equal

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_result import assert_results_equal
from vimseo.analysis_nodes.doe.custom_doe import CustomDOEAnalysisNode
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.analysis_nodes.doe.doe_result import DOEResult
from vimseo.api import create_model
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc2_overall_function,
)
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import generate_dataset
from vimseo.utilities.test_utils import check_result_visualization

N_SAMPLES = 5


@pytest.fixture
def parameter_space():
    """Create a space of parameters with scalar variable ``x1`` uniformly distributed
    over [-1, 1]."""
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, minimum=-1.0, maximum=1.0
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
    doe_analysis_node = DOEAnalysisNode()
    output_names = ["y1"]
    doe_analysis_node.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=output_names,
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )
    return doe_analysis_node


@pytest.mark.parametrize(
    ("input_names", "output_names"),
    [
        ((), ()),
        (["x1"], ()),
        ((), ["y1"]),
    ],
)
def test_custom_doe(tmp_wd, input_dataset, input_names, output_names):
    """Check :class:`.CustomDOEAnalysisNode` in case of specific ``input_names`` or not, and
    specific ``output_names`` or not."""

    model = MockModel("LC2")
    doe_analysis_node = CustomDOEAnalysisNode()

    dataset = doe_analysis_node.execute(
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

    results = BaseAnalysisNode.load_results(
        mock_model_doe.working_directory / "DOEAnalysisNode_result.hdf5"
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


def test_doe_without_n_samples(tmp_wd, parameter_space):
    """Check that the number of samples is not passed to a DOE algorithm without such a
    setting."""
    doe_analysis_node = DOEAnalysisNode()
    doe_analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="StarDOE",
        n_samples=N_SAMPLES,
        algo_settings={"center": {"x1": 0.5}, "two_sided": False},
    )
    dataset = doe_analysis_node.result.dataset
    assert dataset.name == "DOE_MockModel_LC1_StarDOE"
    assert_allclose(
        dataset.get_view(variable_names="x1").to_numpy().ravel(), [0.5, 0.525]
    )


def test_validated_algo_settings(tmp_wd, parameter_space):
    """Check that the metadata store the settings as validated by the DOE algorithm,
    with the default values of the settings specific to this algorithm."""
    doe_analysis_node = DOEAnalysisNode()
    doe_analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="StarDOE",
        algo_settings={"center": {"x1": 0.5}, "two_sided": "false", "n_processes": 1},
    )
    assert doe_analysis_node.result.metadata.settings["algo_settings"] == {
        "center": {"x1": 0.5},
        "relative_step": 0.05,
        "two_sided": False,
        "fallback_step": 0.05,
        "n_processes": 1,
    }
    assert len(doe_analysis_node.result.dataset) == 2


def test_algo_settings_and_dataset_name_from_disk(tmp_wd, parameter_space):
    """Check that the settings of the DOE algorithm and the name of the dataset are
    kept when the result is saved."""
    doe_analysis_node = DOEAnalysisNode()
    doe_analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="StarDOE",
        algo_settings={"two_sided": False},
    )
    doe_analysis_node.save_results()
    result = BaseAnalysisNode.load_results(
        doe_analysis_node.working_directory / "DOEAnalysisNode_result.hdf5"
    )
    assert result.dataset.name == "DOE_MockModel_LC1_StarDOE"
    assert not result.metadata.settings["algo_settings"]["two_sided"]


def test_parameter_space_not_modified(tmp_wd):
    """Check that a DOE does not set the current value of the variables to its best
    sample."""
    parameter_space = ParameterSpace()
    parameter_space.add_variable("x1", lower_bound=-1.0, upper_bound=1.0, value=0.5)
    DOEAnalysisNode().execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="OT_MONTE_CARLO",
        n_samples=N_SAMPLES,
    )
    assert_allclose(parameter_space.get_current_value(["x1"]), [0.5])


def test_doe_algo_settings(tmp_wd, parameter_space):
    """Check that the settings of the DOE algorithm are passed with the number of
    samples."""
    doe_analysis_node = DOEAnalysisNode()
    doe_analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="MorrisDOE",
        n_samples=4,
        algo_settings={"step": 0.25},
    )
    dataset = doe_analysis_node.result.dataset
    assert dataset.name == "DOE_MockModel_LC1_MorrisDOE_4"
    x1 = dataset.get_view(variable_names="x1").to_numpy().ravel()
    assert len(x1) == 4
    # The OAT step of x1 is 0.25 * (1 - (-1)).
    assert abs(x1[1] - x1[0]) == pytest.approx(0.5)


@pytest.fixture
def mesh_size_study(tmp_wd):
    """A DOE varying the input ``x`` of a model with vector outputs and PLOTS."""
    model = create_model("MockCurves", "Dummy")
    input_dataset = IODataset()
    input_dataset.add_variable("x", array([[1.0], [2.0], [3.0]]), IODataset.INPUT_GROUP)
    input_dataset.add_variable("x_1", full((3, 1), 0.5), IODataset.INPUT_GROUP)
    return CustomDOEAnalysisNode().execute(model=model, input_dataset=input_dataset)


def test_doe_result_has_model_figures(mesh_size_study):
    """The description of the model and its figures are stored in the result."""
    assert mesh_size_study.metadata.model.name == "MockCurves"
    assert [plot.get_key() for plot in mesh_size_study.plots] == [
        ("x_history", "y_history")
    ]


def test_parametric_study_figures(mesh_size_study):
    """A DOE varying a single input shows its scalar outputs versus this input,
    and the curves of the PLOTS of the model, superposed for all the samples."""
    figures = mesh_size_study.plot()
    assert "scatter_matrix" in figures
    assert "scalar_outputs_vs_x" in figures
    curves = figures["curves_y_history_vs_x_history"]
    assert [line.name for line in curves.data] == ["x = 1", "x = 2", "x = 3"]
    check_result_visualization(mesh_size_study, "visualization")


def test_without_varying_input(mesh_size_study):
    """Without a single varying input, the samples are not a parametric study."""
    mesh_size_study.dataset.loc[:, ("inputs", "x", 0)] = 1.0
    figures = mesh_size_study.plot()
    assert not any(key.startswith("scalar_outputs_vs") for key in figures)
    assert [line.name for line in figures["curves_y_history_vs_x_history"].data] == [
        "sample 0",
        "sample 1",
        "sample 2",
    ]


def test_without_model_plots(tmp_wd, mock_model_doe):
    """Without vector outputs, no curve is shown."""
    figures = mock_model_doe.result.plot()
    assert not any(key.startswith("curves_") for key in figures)


def test_scatter_matrix_variable_names(mesh_size_study):
    """The variables of the scatter matrix can be selected among the proposed ones."""
    choices = mesh_size_study.get_plot_choices()
    assert choices["scatter_matrix_variable_names"] == ["x", "x_1", "cpu_time"]
    figure = mesh_size_study.plot(scatter_matrix_variable_names=["x", "cpu_time"])[
        "scatter_matrix"
    ]
    assert len(figure.axes) == 4


@pytest.fixture
def factorial_study(tmp_wd):
    """A full factorial DOE of the inputs ``x`` and ``x_1`` of a model with curves,
    plus a sample belonging to no family along ``x``."""
    x = [1.0, 2.0, 3.0, 1.0, 2.0, 3.0, 4.0]
    x_1 = [0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 2.0]
    input_dataset = IODataset()
    input_dataset.add_variable("x", array([x]).T, IODataset.INPUT_GROUP)
    input_dataset.add_variable("x_1", array([x_1]).T, IODataset.INPUT_GROUP)
    return CustomDOEAnalysisNode().execute(
        model=create_model("MockCurves", "Dummy"), input_dataset=input_dataset
    )


def test_families_in_one_figure(factorial_study, caplog):
    """When several inputs vary, the scalar outputs are drawn with a line per family
    of samples differing by the abscissa only, and the curves per family."""
    figures = factorial_study.plot(abscissa_name="x")
    scalars = figures["scalar_outputs_vs_x"]
    assert {trace.name for trace in scalars.data} == {"x_1=0.5", "x_1=1.0"}
    assert all(len(trace.x) == 3 for trace in scalars.data)
    curves = figures["curves_y_history_vs_x_history[x_1=0.5]"]
    assert [line.name for line in curves.data] == ["x = 1", "x = 2", "x = 3"]
    assert "curves_y_history_vs_x_history[x_1=1.0]" in figures
    assert not any(key.startswith("scalar_outputs_vs_x[") for key in figures)
    assert "1 samples belong to no family along x" in caplog.text


def test_one_figure_per_family(factorial_study):
    """The scalar outputs of each family can be drawn in a figure per family."""
    figures = factorial_study.plot(
        abscissa_name="x", family_layout="one_figure_per_family"
    )
    assert "scalar_outputs_vs_x" not in figures
    assert "scalar_outputs_vs_x[x_1=0.5]" in figures
    assert "scalar_outputs_vs_x[x_1=1.0]" in figures


def test_factorial_study_without_abscissa(factorial_study):
    """Without abscissa, the curves of the samples are labelled by the varying
    inputs, and the inputs forming families are proposed as abscissa."""
    figures = factorial_study.plot()
    assert not any(key.startswith("scalar_outputs_vs") for key in figures)
    curves = figures["curves_y_history_vs_x_history"]
    assert curves.data[0].name == "x = 1, x_1 = 0.5"
    assert factorial_study.get_plot_choices()["abscissa_name"] == ["x", "x_1"]


def test_lhs_has_no_family(tmp_wd, caplog):
    """A design varying the inputs jointly has no parametric study."""
    parameter_space = ParameterSpace()
    for name in ("x", "x_1"):
        parameter_space.add_random_variable(
            name, "OTUniformDistribution", minimum=0.0, maximum=1.0
        )
    result = DOEAnalysisNode().execute(
        model=create_model("MockCurves", "Dummy"),
        parameter_space=parameter_space,
        n_samples=4,
    )
    figures = result.plot(abscissa_name="x")
    assert "scatter_matrix" in figures
    assert not any(key.startswith("scalar_outputs_vs") for key in figures)
    assert not any(key.startswith("curves_") for key in figures)
    assert "4 samples belong to no family along x" in caplog.text
    assert "abscissa_name" not in result.get_plot_choices()
    assert result.get_families() == {}


def test_get_families(factorial_study):
    """The families are given along each input forming some."""
    assert factorial_study.get_families() == {
        "x": {"x_1=0.5": [0, 1, 2], "x_1=1.0": [3, 4, 5]},
        "x_1": {"x=1.0": [0, 3], "x=2.0": [1, 4], "x=3.0": [2, 5]},
    }
