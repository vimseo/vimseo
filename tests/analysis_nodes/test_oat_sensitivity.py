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

import re

import plotly.graph_objects as go
import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from numpy.testing import assert_allclose

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_result import assert_results_equal
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.analysis_nodes.sensitivity.oat_sensitivity import OATSensitivityAnalysisNode
from vimseo.analysis_nodes.sensitivity.oat_sensitivity import OATSensitivityInputs
from vimseo.analysis_nodes.sensitivity.oat_sensitivity import OATSensitivitySettings
from vimseo.analysis_nodes.sensitivity.oat_sensitivity_result import (
    OATSensitivityResult,
)
from vimseo.api import create_model
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.utilities.test_utils import check_result_visualization

CENTER = {"x1": 0.5, "x1_maximum_only": 0.5}


@pytest.fixture
def parameter_space():
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", minimum=-1.0, maximum=1.0
    )
    parameter_space.add_random_variable(
        "x1_maximum_only", "OTUniformDistribution", minimum=-1.0, maximum=1.0
    )
    return parameter_space


@pytest.fixture
def oat_analysis_node(tmp_wd, parameter_space):
    """An OAT sensitivity analysis of y1 = 2 * x1 + 5 around x1 = 0.5."""
    analysis_node = OATSensitivityAnalysisNode()
    analysis_node.execute(
        inputs=OATSensitivityInputs(
            model=MockModel("LC1"), parameter_space=parameter_space
        ),
        settings=OATSensitivitySettings(output_names=["y1"], center=CENTER),
    )
    return analysis_node


def test_indices(oat_analysis_node):
    """Check the indices of a linear output around a center."""
    result = oat_analysis_node.result
    assert result.two_sided
    assert_allclose(result.center["x1"], [0.5])
    assert_allclose(result.input_steps["x1"], [0.025])
    indices = result.indices
    assert_allclose(indices["delta_f_plus"]["y1"][0]["x1"], [0.05])
    assert_allclose(indices["delta_f_minus"]["y1"][0]["x1"], [-0.05])
    assert_allclose(indices["delta_f"]["y1"][0]["x1"], [0.05])
    assert_allclose(indices["relative_delta_f"]["y1"][0]["x1"], [0.05 / 6])
    assert_allclose(indices["gradient"]["y1"][0]["x1"], [2.0])
    assert_allclose(indices["delta_f"]["y1"][0]["x1_maximum_only"], [0.0])
    assert result.sort_input_variables("y1") == ["x1", "x1_maximum_only"]
    assert len(result.dataset) == 5
    text = str(result)
    assert "by decreasing absolute centered variation delta_f:" in text
    assert "For output y1[0]: x1 (0.05), x1_maximum_only (0)." in text
    # The index blocks are separated by a blank line and their tables are indented.
    assert "\n\nIndex delta_f_plus:\n   " in text
    assert result.get_zero_center_names() == []
    assert "Warning:" not in text
    assert "inputs_with_non_relative_step" not in result.metadata.report


def _prepare_star_doe(parameter_space, **algo_settings):
    """Return a DOEAnalysisNode that executed a star DOE of MockModel in advance.

    The DOE computes all the outputs of the model, including its metadata.
    """
    doe_analysis_node = DOEAnalysisNode()
    doe_analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        algo="StarDOE",
        algo_settings={"center": CENTER, **algo_settings},
    )
    return doe_analysis_node


def test_prepared_doe(tmp_wd, oat_analysis_node, parameter_space):
    """Check that the result of a star DOE prepared in advance gives the same
    indices, the metadata of the model being filtered out."""
    doe_result = _prepare_star_doe(parameter_space).result
    analysis_node = OATSensitivityAnalysisNode()
    analysis_node.execute(doe_result=doe_result, output_names=["y1"])
    assert_results_equal(analysis_node.result.indices, oat_analysis_node.result.indices)
    assert analysis_node.result.two_sided
    assert (
        analysis_node.result.metadata.report["doe_dataset_name"]
        == doe_result.dataset.name
    )
    # The prepared DOE is saved as the result of the DOE sub-analysis node.
    assert analysis_node._sub_analysis_nodes["DOEAnalysisNode"].result is doe_result
    analysis_node.save_results()
    assert (
        analysis_node.working_directory
        / "DOEAnalysisNode"
        / "DOEAnalysisNode_result.hdf5"
    ).is_file()


def test_prepared_one_sided_doe_from_disk(tmp_wd, parameter_space):
    """Check that a one-sided star DOE saved on the disk is read as one-sided.

    Whether the star is two-sided is read from the settings of the DOE algorithm.
    """
    doe_analysis_node = _prepare_star_doe(parameter_space, two_sided=False)
    doe_analysis_node.save_results()
    doe_result = BaseAnalysisNode.load_results(
        doe_analysis_node.working_directory / "DOEAnalysisNode_result.hdf5"
    )
    analysis_node = OATSensitivityAnalysisNode()
    analysis_node.execute(doe_result=doe_result, output_names=["y1"])
    assert analysis_node.result.two_sided is False
    assert "delta_f_minus" not in analysis_node.result.indices
    assert_allclose(analysis_node.result.indices["gradient"]["y1"][0]["x1"], [2.0])


def test_prepared_doe_missing_sample(tmp_wd, parameter_space):
    """Check that a star DOE with a missing sample, e.g. a failed evaluation, is
    rejected."""
    doe_result = _prepare_star_doe(parameter_space).result
    doe_result.dataset = doe_result.dataset.iloc[:-1]
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The star DOE has 4 samples, whereas a two-sided star with 2 input "
            "components has 5; an evaluation of the model may have failed."
        ),
    ):
        OATSensitivityAnalysisNode().execute(doe_result=doe_result, output_names=["y1"])


def test_prepared_doe_nan_output(tmp_wd, parameter_space):
    """Check that a star DOE with a NaN output, e.g. a failed evaluation, is
    rejected."""
    doe_result = _prepare_star_doe(parameter_space).result
    doe_result.dataset.loc[2, (IODataset.OUTPUT_GROUP, "y1", 0)] = float("nan")
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The sensitivity analysis 'OAT' cannot use the samples [2] of the DOE"
        ),
    ):
        OATSensitivityAnalysisNode().execute(doe_result=doe_result, output_names=["y1"])


def test_prepared_doe_with_star_settings(tmp_wd, parameter_space, caplog):
    """Check that the settings of the star DOE are ignored with a prepared DOE."""
    OATSensitivityAnalysisNode().execute(
        doe_result=_prepare_star_doe(parameter_space).result, relative_step=0.1
    )
    assert "The settings ['relative_step'] are ignored" in caplog.text


@pytest.mark.parametrize(
    ("algo", "algo_settings"),
    [("OT_MONTE_CARLO", {}), ("OATDOE", {"initial_point": array([0.5, 0.5])})],
)
def test_not_a_star(tmp_wd, parameter_space, algo, algo_settings):
    """Check that the result of a DOE other than StarDOE is rejected."""
    doe_analysis_node = DOEAnalysisNode()
    doe_analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        algo=algo,
        n_samples=4,
        algo_settings=algo_settings,
    )
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The sensitivity analysis 'OAT' requires the samples of a DOE generated "
            f"by 'StarDOE', whereas they were generated by '{algo}'."
        ),
    ):
        OATSensitivityAnalysisNode().execute(doe_result=doe_analysis_node.result)


def test_no_model_nor_doe(tmp_wd):
    """Check that a model or a prepared DOE is required."""
    with pytest.raises(ValueError, match="Either a model or the result"):
        OATSensitivityAnalysisNode().execute()


@pytest.mark.parametrize(
    ("two_sided", "gradient", "steps"),
    [
        # The centered difference is exact for a quadratic function.
        (True, [12.0, 12.0, 12.0], [0.05, 0.1, 0.15]),
        (False, [12.05, 12.1, 12.15], [0.05, 0.1, 0.15]),
    ],
)
def test_vector_input_and_output(tmp_wd, two_sided, gradient, steps):
    """Check the indices of y5 = [s, s**2, s**3] with s = sum(x3) and x3 = [1, 2, 3].

    The gradient of s**2 is 2s = 12; its one-sided estimation is 2s+h.
    """
    parameter_space = ParameterSpace()
    parameter_space.add_variable(
        "x3", size=3, lower_bound=0.0, upper_bound=10.0, value=[1.0, 2.0, 3.0]
    )
    analysis_node = OATSensitivityAnalysisNode()
    analysis_node.execute(
        model=create_model("MockModelPersistent", "LC1"),
        parameter_space=parameter_space,
        output_names=["y5"],
        two_sided=two_sided,
    )
    result = analysis_node.result
    assert result.two_sided is two_sided
    assert_allclose(result.input_steps["x3"], steps)
    assert_allclose(result.indices["gradient"]["y5"][0]["x3"], [1.0, 1.0, 1.0])
    assert_allclose(result.indices["gradient"]["y5"][1]["x3"], gradient)
    table = result.get_indices_dataframe("gradient")
    assert list(table.columns) == ["y5[0]", "y5[1]", "y5[2]"]
    assert list(table.index) == ["x3[0]", "x3[1]", "x3[2]"]


def test_zero_output_at_center(tmp_wd, caplog):
    """Check that the relative indices are NaN when the output is zero at the
    center."""
    parameter_space = ParameterSpace()
    # y4 = sum(x3) is zero at the center.
    parameter_space.add_variable(
        "x3", size=3, lower_bound=-10.0, upper_bound=10.0, value=[1.0, -1.0, 0.0]
    )
    analysis_node = OATSensitivityAnalysisNode()
    analysis_node.execute(
        model=create_model("MockModelPersistent", "LC1"),
        parameter_space=parameter_space,
        output_names=["y4"],
    )
    assert_allclose(analysis_node.result.input_steps["x3"], [0.05, 0.05, 1.0])
    assert_allclose(
        analysis_node.result.indices["gradient"]["y4"][0]["x3"], [1.0, 1.0, 1.0]
    )
    assert_allclose(
        analysis_node.result.indices["relative_delta_f"]["y4"][0]["x3"],
        [float("nan")] * 3,
    )
    assert "The output y4 is zero at the center of the star" in caplog.text
    # The step of x3[2], whose center is zero, is not relative to its center.
    assert "The center of ['x3[2]'] is zero: its step is not relative" in caplog.text
    result = analysis_node.result
    assert result.metadata.report["inputs_with_non_relative_step"] == ["x3[2]"]
    assert "Warning: the steps of ['x3[2]'] are not relative" in str(result)


def test_serialization(oat_analysis_node):
    """Check that an OAT sensitivity result can be serialized to HDF5."""
    oat_analysis_node.save_results()
    result = BaseAnalysisNode.load_results(
        oat_analysis_node.working_directory / "OATSensitivityAnalysisNode_result.hdf5"
    )
    assert isinstance(result, OATSensitivityResult)
    assert_results_equal(result.indices, oat_analysis_node.result.indices)
    assert result.two_sided


def test_plot(oat_analysis_node):
    """Check the tornado diagram."""
    figures = oat_analysis_node.result.plot(
        directory_path=oat_analysis_node.working_directory, save=True
    )
    assert list(figures) == ["tornado_y1"]
    assert [trace.name for trace in figures["tornado_y1"].data] == [
        "+ step",
        "- step",
    ]
    colors = [trace.marker.color for trace in figures["tornado_y1"].data]
    assert None not in colors
    assert colors[0] != colors[1]
    assert (oat_analysis_node.working_directory / "tornado_y1.html").is_file()


def test_result_visualization(tmp_wd, oat_analysis_node):
    """Check that an OAT result can be visualized once loaded from a file."""
    check_result_visualization(oat_analysis_node.result, "visualization")
    assert oat_analysis_node.result.get_plot_choices() == {"output_names": ["y1"]}
    tables = oat_analysis_node.result.to_dataframes()
    assert "indices_delta_f" in tables
    assert "y1" in tables["indices_delta_f"].columns
    assert "delta_f.y1.x1" in oat_analysis_node.result.get_key_values()


def test_variables_not_sorted(tmp_wd):
    """Check the indices when the variables are not sorted alphabetically.

    The samples of the DOE are ordered like the variables of the parameter space.
    """
    parameter_space = ParameterSpace()
    for name in ["x1_maximum_only", "x1"]:
        parameter_space.add_random_variable(
            name, "OTUniformDistribution", minimum=-1.0, maximum=1.0
        )
    analysis_node = OATSensitivityAnalysisNode()
    analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        center=CENTER,
    )
    assert list(analysis_node.result.center) == ["x1_maximum_only", "x1"]
    assert_allclose(analysis_node.result.indices["gradient"]["y1"][0]["x1"], [2.0])
    assert_allclose(
        analysis_node.result.indices["gradient"]["y1"][0]["x1_maximum_only"], [0.0]
    )


def test_plot_one_sided_and_shown(tmp_wd, parameter_space, monkeypatch):
    """Check the tornado diagram of a one-sided analysis, shown and not saved."""
    shown = []
    monkeypatch.setattr(go.Figure, "show", lambda figure: shown.append(figure))
    analysis_node = OATSensitivityAnalysisNode()
    analysis_node.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        output_names=["y1"],
        center=CENTER,
        two_sided=False,
    )
    figures = analysis_node.result.plot(show=True)
    assert [trace.name for trace in figures["tornado_y1"].data] == ["+ step"]
    assert shown == [figures["tornado_y1"]]
    assert not (analysis_node.working_directory / "tornado_y1.html").exists()


def test_parameter_space_not_modified(tmp_wd):
    """Check that an analysis does not move the center of a next one.

    A DOE sets the current value of the variables to its best sample, here the one
    minimizing y1 = 2 * x1 + 5.
    """
    parameter_space = ParameterSpace()
    parameter_space.add_variable("x1", lower_bound=-1.0, upper_bound=1.0, value=0.5)
    parameter_space.add_random_variable(
        "x1_maximum_only", "OTUniformDistribution", minimum=-1.0, maximum=1.0
    )
    centers = []
    for _ in range(2):
        analysis_node = OATSensitivityAnalysisNode()
        analysis_node.execute(
            model=MockModel("LC1"), parameter_space=parameter_space, output_names=["y1"]
        )
        centers.append(analysis_node.result.center)

    assert_results_equal(centers[0], centers[1])
    assert_allclose(centers[0]["x1"], [0.5])
    assert_allclose(centers[0]["x1_maximum_only"], [0.0])
    assert_allclose(parameter_space.get_current_value(["x1"]), [0.5])
