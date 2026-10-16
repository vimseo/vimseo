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

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from numpy.testing import assert_allclose
from pandas.testing import assert_frame_equal

from vimseo.api import create_model
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.doe.doe_result import DOEResult
from vimseo.tools.sensitivity.indices import indices_to_dataframe
from vimseo.tools.sensitivity.sensitivity import SensitivityTool
from vimseo.tools.sensitivity.sensitivity import SensitivityToolInputs
from vimseo.tools.sensitivity.sensitivity import SensitivityToolSettings
from vimseo.tools.sensitivity.sensitivity_result import SensitivityResult


@pytest.fixture
def parameter_space():
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, minimum=-1.0, maximum=1.0
    )
    parameter_space.add_random_variable(
        "x1_maximum_only", "OTUniformDistribution", size=1, minimum=-1.0, maximum=1.0
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
        "x1", "OTUniformDistribution", minimum=0.0, maximum=2.0
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


def test_save_and_load_result(tmp_wd, sensitivity_tool):
    """Check that a sensitivity analysis can be saved and that a new instance can be
    created and loaded from saved data.

    A plot can be generated from the new instance.
    """
    sensitivity_tool.save_results()
    results = BaseTool.load_results(
        sensitivity_tool.working_directory / "SensitivityTool_result.hdf5"
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


def test_serialization(tmp_wd, sensitivity_tool):
    """Check that a SensitivityResult can be serialized to hdf5."""
    result = sensitivity_tool.result
    result.to_hdf5("result.hdf5")
    serialized_result = SensitivityResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)


def _prepare_doe(parameter_space, algo, n_samples, output_names=(), **algo_settings):
    """Return the result of a DOE of MockModel prepared in advance."""
    doe_tool = DOETool()
    doe_tool.execute(
        model=MockModel("LC1"),
        parameter_space=parameter_space,
        algo=algo,
        n_samples=n_samples,
        output_names=list(output_names),
        algo_settings=algo_settings,
    )
    return doe_tool.result


def test_morris_prepared_doe(tmp_wd, parameter_space, sensitivity_tool):
    """Check a Morris analysis from the result of a MorrisDOE prepared in advance.

    The DOE computes all the outputs of the model, including its metadata, which are
    filtered out.
    """
    doe_result = _prepare_doe(parameter_space, "MorrisDOE", 15)
    tool = SensitivityTool()
    tool.execute(
        inputs=SensitivityToolInputs(doe_result=doe_result),
        settings=SensitivityToolSettings(sensitivity_algo="Morris"),
    )
    assert tool.result.metadata.report["output_names"] == ["y1"]
    assert tool.result.metadata.report["doe_dataset_name"] == doe_result.dataset.name
    assert tool.result.variable_dimensions == {
        "x1": 1,
        "x1_maximum_only": 1,
        "y1": 1,
    }
    for name in ["x1", "x1_maximum_only"]:
        assert tool.result.indices.mu["y1"][0][name] == pytest.approx(
            sensitivity_tool.result.indices.mu["y1"][0][name]
        )
    tool.result.analysis.compute_indices(normalize=True)


def test_morris_prepared_doe_step(tmp_wd, parameter_space):
    """Check that the relative step of a prepared MorrisDOE is read from its settings.

    The elementary effects of y1 = 2 * x1 + 5 with x1 in [-1, 1] are 4 times the step.
    """
    tool = SensitivityTool()
    tool.execute(
        doe_result=_prepare_doe(parameter_space, "MorrisDOE", 15, ["y1"], step=0.1),
        sensitivity_algo="Morris",
    )
    assert tool.result.analysis.dataset.misc["step"] == pytest.approx(0.1)
    assert tool.result.indices.mu_star["y1"][0]["x1"] == pytest.approx(0.4)


def test_morris_prepared_doe_missing_sample(tmp_wd, parameter_space):
    """Check that a Morris DOE with a missing sample, e.g. a failed evaluation, is
    rejected."""
    doe_result = _prepare_doe(parameter_space, "MorrisDOE", 15, ["y1"])
    doe_result.dataset = doe_result.dataset.iloc[:-1]
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The Morris DOE has 14 samples, whereas its trajectories have 3 samples "
            "each; an evaluation of the model may have failed."
        ),
    ):
        SensitivityTool().execute(doe_result=doe_result, sensitivity_algo="Morris")


def test_morris_prepared_doe_nan_output(tmp_wd, parameter_space):
    """Check that a Morris DOE with a NaN output, e.g. a failed evaluation, is
    rejected."""
    doe_result = _prepare_doe(parameter_space, "MorrisDOE", 15, ["y1"])
    doe_result.dataset.loc[4, (IODataset.OUTPUT_GROUP, "y1", 0)] = float("nan")
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The sensitivity analysis 'Morris' cannot use the samples [4] of the DOE"
        ),
    ):
        SensitivityTool().execute(doe_result=doe_result, sensitivity_algo="Morris")


def test_hsic_prepared_doe_nan_output(tmp_wd, parameter_space, caplog):
    """Check that a HSIC analysis removes the samples with a NaN output."""
    doe_result = _prepare_doe(parameter_space, "OT_MONTE_CARLO", 10, ["y1"])
    doe_result.dataset.loc[3, (IODataset.OUTPUT_GROUP, "y1", 0)] = float("nan")
    tool = SensitivityTool()
    tool.execute(doe_result=doe_result, sensitivity_algo="HSIC")
    assert len(tool.result.analysis.dataset) == 9
    assert "The samples [3] of the DOE are removed" in caplog.text
    assert set(tool.result.indices.hsic["y1"][0]) == {"x1", "x1_maximum_only"}


def test_hsic_prepared_doe(tmp_wd, parameter_space):
    """Check a HSIC analysis from the i.i.d. samples of a Monte Carlo sampling
    prepared in advance."""
    tool = SensitivityTool()
    tool.execute(
        doe_result=_prepare_doe(parameter_space, "OT_MONTE_CARLO", 10, ["y1"]),
        sensitivity_algo="HSIC",
    )
    assert set(tool.result.indices.hsic["y1"][0]) == {"x1", "x1_maximum_only"}


@pytest.mark.parametrize(
    ("sensitivity_algo", "expected_algos"),
    [
        ("Morris", "'MorrisDOE'"),
        ("HSIC", "'OT_MONTE_CARLO' or 'OT_RANDOM' or 'MC' or 'Unstructured'"),
    ],
)
def test_prepared_doe_unsuitable_algo(
    tmp_wd, parameter_space, sensitivity_algo, expected_algos
):
    """Check that an analysis rejects a DOE whose algorithm is not suitable, here a
    Latin Hypercube Sampling."""
    with pytest.raises(
        ValueError,
        match=re.escape(
            f"The sensitivity analysis '{sensitivity_algo}' requires the samples of a "
            f"DOE generated by {expected_algos}, "
            "whereas they were generated by 'OT_OPT_LHS'."
        ),
    ):
        SensitivityTool().execute(
            doe_result=_prepare_doe(parameter_space, "OT_OPT_LHS", 6, ["y1"]),
            sensitivity_algo=sensitivity_algo,
        )


def test_prepared_doe_unknown_algo(tmp_wd, parameter_space):
    """Check that a DOE whose algorithm is unknown is rejected."""
    doe_result = DOEResult(
        dataset=_prepare_doe(parameter_space, "OT_MONTE_CARLO", 4, ["y1"]).dataset
    )
    with pytest.raises(ValueError, match="by an unknown DOE algorithm"):
        SensitivityTool().execute(doe_result=doe_result, sensitivity_algo="HSIC")


def test_no_model_nor_doe(tmp_wd):
    """Check that a model or a prepared DOE is required."""
    with pytest.raises(ValueError, match="Either a model or the result"):
        SensitivityTool().execute(sensitivity_algo="HSIC")


def test_morris_prepared_doe_variables_not_sorted(tmp_wd):
    """Check a Morris analysis from a prepared DOE whose variables are not sorted
    alphabetically.

    The samples of the DOE are ordered like the variables of the parameter space.
    """
    parameter_space = ParameterSpace()
    for name in ["x1_maximum_only", "x1"]:
        parameter_space.add_random_variable(
            name, "OTUniformDistribution", minimum=-1.0, maximum=1.0
        )
    tool = SensitivityTool()
    tool.execute(
        doe_result=_prepare_doe(parameter_space, "MorrisDOE", 15, ["y1"]),
        sensitivity_algo="Morris",
    )
    assert tool.result.indices.mu["y1"][0]["x1"] == pytest.approx(0.2)
    assert tool.result.indices.mu["y1"][0]["x1_maximum_only"] == pytest.approx(0.0)


def test_indices_dataframe(tmp_wd, sensitivity_tool):
    """Check the table of the indices, by default the main ones."""
    result = sensitivity_tool.result
    table = result.get_indices_dataframe()
    assert list(table.columns) == ["y1"]
    assert list(table.index) == ["x1", "x1_maximum_only"]
    assert table.loc["x1", "y1"] == pytest.approx(
        float(result.indices.mu_star["y1"][0]["x1"][0])
    )
    sigma = result.get_indices_dataframe("sigma")
    assert sigma.loc["x1", "y1"] == pytest.approx(
        float(result.indices.sigma["y1"][0]["x1"][0])
    )


def test_indices_dataframe_loaded_result(tmp_wd, sensitivity_tool):
    """Check the table of the indices of a result loaded from the disk.

    The HDF5 serialization does not preserve the order of the inputs.
    """
    sensitivity_tool.save_results()
    result = BaseTool.load_results(
        sensitivity_tool.working_directory / "SensitivityTool_result.hdf5"
    )
    assert_frame_equal(
        result.get_indices_dataframe(),
        sensitivity_tool.result.get_indices_dataframe(),
        check_like=True,
    )


def test_indices_dataframe_hsic_vector(tmp_wd):
    """Check the table of the main HSIC indices for vector inputs and outputs."""
    parameter_space = ParameterSpace()
    parameter_space.add_random_vector(
        "x3", "OTNormalDistribution", size=3, mu=[1.0, 1.5, 1.9], sigma=[0.2]
    )
    tool = SensitivityTool()
    tool.execute(
        model=create_model("MockModelPersistent", "LC1"),
        parameter_space=parameter_space,
        sensitivity_algo="HSIC",
        n_samples=10,
        output_names=["y5"],
    )
    table = tool.result.get_indices_dataframe()
    assert list(table.columns) == ["y5[0]", "y5[1]", "y5[2]"]
    assert list(table.index) == ["x3[0]", "x3[1]", "x3[2]"]
    assert table.loc["x3[1]", "y5[2]"] == pytest.approx(
        float(tool.result.indices.r2_hsic["y5"][2]["x3"][1])
    )


def test_unhandled_algo(tmp_wd, parameter_space):
    """Check that a sensitivity analysis other than Morris and HSIC is rejected."""
    with pytest.raises(ValueError, match="Sobol is not handled"):
        SensitivityTool().execute(
            model=MockModel("LC1"),
            parameter_space=parameter_space,
            sensitivity_algo="Sobol",
        )


def test_prepared_doe_missing_output(tmp_wd, parameter_space):
    """Check that the outputs of the analysis must be in the prepared DOE."""
    with pytest.raises(ValueError, match=r"The outputs \['y2'\] are missing"):
        SensitivityTool().execute(
            doe_result=_prepare_doe(parameter_space, "OT_MONTE_CARLO", 4, ["y1"]),
            sensitivity_algo="HSIC",
            output_names=["y2"],
        )


def test_prepared_doe_without_output_group(tmp_wd):
    """Check that the prepared DOE must have an output group."""
    doe_result = DOEResult(
        dataset=Dataset.from_array(
            array([[0.0], [1.0]]),
            ["x1"],
            variable_names_to_group_names={"x1": IODataset.INPUT_GROUP},
        )
    )
    doe_result.metadata.settings["algo"] = "OT_MONTE_CARLO"
    with pytest.raises(ValueError, match="must have a group 'outputs'"):
        SensitivityTool().execute(
            doe_result=doe_result, sensitivity_algo="HSIC", output_names=["x1"]
        )


def test_indices_dataframe_constant_output_component():
    """Check that the constant output components are not in the table."""
    table = indices_to_dataframe({"y": [{"x": array([1.0])}, None]})
    assert list(table.columns) == ["y[0]"]
    assert table.loc["x", "y[0]"] == pytest.approx(1.0)


def test_hsic_dataset(tmp_wd, parameter_space, caplog):
    """Check a HSIC analysis from samples not generated by a DOE.

    The samples are wrapped into a DOE result whose DOE algorithm is 'Unstructured',
    saved as the result of the DOE sub-tool.
    """
    doe_result = _prepare_doe(parameter_space, "OT_MONTE_CARLO", 10, ["y1"])
    reference = SensitivityTool()
    reference.execute(
        inputs=SensitivityToolInputs(doe_result=doe_result),
        settings=SensitivityToolSettings(sensitivity_algo="HSIC"),
    )
    tool = SensitivityTool()
    tool.execute(
        inputs=SensitivityToolInputs(dataset=doe_result.dataset),
        settings=SensitivityToolSettings(sensitivity_algo="HSIC"),
    )
    assert "which cannot be checked" in caplog.text
    assert_results_equal(tool.result.indices.hsic, reference.result.indices.hsic)
    doe_tool_result = tool._subtools["DOETool"].result
    assert doe_tool_result.metadata.settings["algo"] == "Unstructured"
    tool.save_results()
    assert (tool.working_directory / "DOETool" / "DOETool_result.hdf5").is_file()


def test_morris_dataset(tmp_wd, parameter_space):
    """Check that a Morris analysis rejects samples not generated by a DOE."""
    dataset = _prepare_doe(parameter_space, "MorrisDOE", 15, ["y1"]).dataset
    with pytest.raises(
        ValueError, match="whereas they were generated by 'Unstructured'"
    ):
        SensitivityTool().execute(
            inputs=SensitivityToolInputs(dataset=dataset),
            settings=SensitivityToolSettings(sensitivity_algo="Morris"),
        )


def test_doe_result_and_dataset(tmp_wd, parameter_space):
    """Check that a DOE result and a dataset cannot be provided together."""
    doe_result = _prepare_doe(parameter_space, "OT_MONTE_CARLO", 4, ["y1"])
    with pytest.raises(ValueError, match="cannot be provided together"):
        SensitivityTool().execute(
            inputs=SensitivityToolInputs(
                doe_result=doe_result, dataset=doe_result.dataset
            ),
            settings=SensitivityToolSettings(sensitivity_algo="HSIC"),
        )


def test_hsic_without_n_samples(tmp_wd, parameter_space):
    """Check that a HSIC analysis sampling the model requires a number of samples."""
    with pytest.raises(ValueError, match="requires a number of samples"):
        SensitivityTool().execute(
            inputs=SensitivityToolInputs(
                model=MockModel("LC1"), parameter_space=parameter_space
            ),
            settings=SensitivityToolSettings(sensitivity_algo="HSIC"),
        )


def test_save_generated_doe(tmp_wd, sensitivity_tool):
    """Check that the DOE executed by the tool is saved as a sub-tool result."""
    doe_result = sensitivity_tool._subtools["DOETool"].result
    assert doe_result.metadata.settings["algo"] == "MorrisDOE"
    sensitivity_tool.save_results()
    assert (
        sensitivity_tool.working_directory / "DOETool" / "DOETool_result.hdf5"
    ).is_file()


def test_save_prepared_doe(tmp_wd, parameter_space):
    """Check that a DOE prepared in advance is saved as a sub-tool result."""
    doe_result = _prepare_doe(parameter_space, "OT_MONTE_CARLO", 10, ["y1"])
    tool = SensitivityTool()
    tool.execute(
        inputs=SensitivityToolInputs(doe_result=doe_result),
        settings=SensitivityToolSettings(sensitivity_algo="HSIC"),
    )
    assert tool._subtools["DOETool"].result is doe_result
    tool.save_results()
    assert (tool.working_directory / "DOETool" / "DOETool_result.hdf5").is_file()
