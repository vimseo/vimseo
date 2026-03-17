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
from numpy import array
from numpy.testing import assert_allclose

from vimseo.api import create_model
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.sensitivity.sensitivity import SensitivityTool
from vimseo.tools.sensitivity.sensitivity import SensitivityToolInputs
from vimseo.tools.sensitivity.sensitivity import SensitivityToolSettings


@pytest.fixture
def parameter_space():
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, lower=-1.0, upper=1.0
    )
    parameter_space.add_random_variable(
        "x1_maximum_only", "OTUniformDistribution", size=1, lower=-1.0, upper=1.0
    )
    return parameter_space


@pytest.fixture
def sensitivity_tool(parameter_space):
    model = MockModel("LC1")
    sensitivity_tool = SensitivityTool()
    sensitivity_tool.execute(
        model=model,
        parameter_space=parameter_space,
        sensitivity_algo="MorrisAnalysis",
        n_replicates=5,
    )
    return sensitivity_tool


def test_mockmodel_morris(tmp_wd, sensitivity_tool):
    assert pytest.approx(
        sensitivity_tool.result.indices.mu["y1"][0]["x1"], 0.01
    ) == array([0.2])


@pytest.mark.skip(reason="OATAnalysis needs to be updated versus Gemseo.")
def test_oat_mockmodel_parameter_space(tmp_wd, parameter_space):
    model = MockModel("LC1")

    sensitivity_tool = SensitivityTool()

    out = sensitivity_tool.execute(
        model=model,
        parameter_space=parameter_space,
        algo="OATAnalysis",
        algo_options={"CoV": 0.1},
    ).indices

    assert pytest.approx(out["delta_f"]["y1"]["x1"], 0.001) == array([0.4])
    assert pytest.approx(out["relative_delta_f"]["y1"]["x1"], 0.1) == array([0.08])


@pytest.mark.skip(reason="OATAnalysis needs to be updated versus Gemseo.")
def test_oat_mockmodel_input_data(tmp_wd):
    model = MockModel("LC1")

    parameter_space = None

    sensitivity_tool = SensitivityTool()

    out = sensitivity_tool.execute(
        model=model,
        parameter_space=parameter_space,
        algo="OATAnalysis",
        algo_options={"input_data": {"x1": array([0.5])}, "CoV": 0.1},
    ).indices

    assert pytest.approx(out["LC1"]["delta_f"]["y1"]["x1"], 0.001) == array([0.1])
    assert pytest.approx(out["LC1"]["relative_delta_f"]["y1"]["x1"], 0.1) == array([
        0.016
    ])


def test_hsic(tmp_wd, parameter_space):
    """Check that a HSIC sensitivity analysis can be performed."""
    model = MockModel("LC1")
    sensitivity_tool = SensitivityTool()
    sensitivity_tool.execute(
        inputs=SensitivityToolInputs(parameter_space=parameter_space, model=model),
        settings=SensitivityToolSettings(sensitivity_algo="HSIC", n_samples=10),
    )
    assert sensitivity_tool.result.indices.hsic["y1"][0]["x1"] == pytest.approx(
        0.1138726
    )


@pytest.mark.parametrize(
    ("sensitivity_algo", "settings", "expected_indices"),
    [
        (
            "Morris",
            {"n_replicates": 5},
            {
                "attr": "mu",
                "x1": array([0.0]),
                "x3": array([0.040035, 0.043367, 0.122493]),
            },
        ),
        (
            "HSIC",
            {"n_samples": 10},
            {
                "attr": "hsic",
                "x1": array([0.00417611]),
                "x3": array([-0.00311482, -0.01120872, -0.00406003]),
            },
        ),
    ],
)
def test_sensitivity_vector_input(tmp_wd, sensitivity_algo, settings, expected_indices):
    """Check that a sensitivity analysis can be performed on a vector input."""
    model = create_model("MockModelPersistent", "LC1")
    parameter_space = ParameterSpace()
    parameter_space.add_random_vector(
        "x3",
        "OTNormalDistribution",
        size=3,
        mu=[1.0, 1.5, 1.9],
        sigma=[0.2],
    )
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", lower=0.0, upper=2.0
    )
    sensitivity_tool = SensitivityTool()
    sensitivity_tool.execute(
        inputs=SensitivityToolInputs(parameter_space=parameter_space, model=model),
        settings=SensitivityToolSettings(
            sensitivity_algo=sensitivity_algo, output_names=["y4", "y5"], **settings
        ),
    )
    for name in ["x1", "x3"]:
        assert_allclose(
            getattr(sensitivity_tool.result.indices, expected_indices["attr"])["y4"][0][
                name
            ],
            expected_indices[name],
            rtol=1e-5,
        )
    sensitivity_tool.save_results()
    sensitivity_tool.plot_results(
        sensitivity_tool.result, output_names=["y4"], save=True, show=False
    )


def test_save_and_load_pickle(tmp_wd, sensitivity_tool):
    """Check that a sensitivity analysis can be saved and that a new instance can be
    created and loaded from saved data.

    A plot can be generated from the new instance.
    """
    sensitivity_tool.save_results()
    results = BaseTool.load_results(
        sensitivity_tool.working_directory / "SensitivityTool_result.pickle"
    )
    assert pytest.approx(results.indices.mu["y1"][0]["x1"], 0.01) == array([0.2])


def test_plots(tmp_wd, sensitivity_tool):
    sensitivity_tool.plot_results(
        sensitivity_tool.result,
        save=True,
        show=False,
        output_names=["y1"],
        standardize=True,
    )
    expected_filenames = ["bar_plot.html", "radar_chart.png", "standard_plot_y1.png"]
    for name in expected_filenames:
        assert (sensitivity_tool.working_directory / name).is_file()
