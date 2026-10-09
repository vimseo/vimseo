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
from gemseo.utils.metrics.dataset_metric import DatasetMetric
from gemseo.utils.metrics.metric_factory import MetricFactory
from numpy import array
from numpy import linspace
from numpy.testing import assert_allclose

from vimseo.api import create_model
from vimseo.problems.mock.mock_reference_data import MOCK_REFERENCE_DIR
from vimseo.storage_management.tool_archive.directory_tool_archive import (
    DirectoryToolArchive,
)
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrame
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrameSettings
from vimseo.tools.validation.validation_point_result import ValidationPointResult
from vimseo.tools.validation_case.validation_case import DeterministicValidationCase
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseInputs,
)
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseSettings,
)
from vimseo.tools.validation_case.validation_case_result import ValidationCaseResult
from vimseo.utilities.metrics.error_metrics import RelativeErrorMetric
from vimseo.utilities.test_utils import check_result_visualization


@pytest.fixture
def reference_data():
    """Create reference data."""
    return (
        ReaderFileDataFrame()
        .execute(
            settings=ReaderFileDataFrameSettings(
                file_name=MOCK_REFERENCE_DIR / "MockModelPersistent_LC1.csv",
                variable_names=["x3", "x1", "x2", "y4"],
                variable_names_to_group_names={
                    "x1": IODataset.INPUT_GROUP,
                    "x2": IODataset.INPUT_GROUP,
                    "x3": IODataset.INPUT_GROUP,
                    "y4": IODataset.OUTPUT_GROUP,
                },
                variable_names_to_n_components={
                    "x3": 3,
                },
            ),
        )
        .dataset
    )


@pytest.fixture
def stochastic_case_result():
    """A mock ValidationCaseResult set from stochastic validation points."""
    measured_data = IODataset.from_array(
        [[1.0, 2.0], [3.0, 4.0]],
        variable_names=["x3", "y1"],
        variable_names_to_group_names={
            "x3": IODataset.INPUT_GROUP,
            "y1": IODataset.OUTPUT_GROUP,
        },
    )
    simulated_data = IODataset.from_array(
        [[1.5, 2.5], [3.5, 4.5]],
        variable_names=["x3", "y1"],
        variable_names_to_group_names={
            "x3": IODataset.INPUT_GROUP,
            "y1": IODataset.OUTPUT_GROUP,
        },
    )
    dm = DatasetMetric(
        RelativeErrorMetric,
        variable_names=["y1"],
    )
    mean_metric = MetricFactory().create("MeanMetric", dm)

    point_1 = ValidationPointResult(
        nominal_data={
            "x1_vector": linspace(0, 1, 5),
            "x2": array([1.0]),
            "x3": 2.0,
            "x4": "foo",
        },
        measured_data=measured_data,
        simulated_data=simulated_data,
        integrated_metrics={
            "RelativeErrorMetric": {
                "y1": mean_metric.compute(measured_data, simulated_data)
            }
        },
    )
    point_1.metadata.settings["metric_names"] = ["RelativeErrorMetric"]
    point_1.metadata.report["measured_output_names"] = ["y1"]

    measured_data = IODataset.from_array(
        [[1.1, 2.1], [3.1, 4.1]],
        variable_names=["x3", "y1"],
        variable_names_to_group_names={
            "x3": IODataset.INPUT_GROUP,
            "y1": IODataset.OUTPUT_GROUP,
        },
    )
    simulated_data = IODataset.from_array(
        [[1.6, 2.6], [3.6, 4.6]],
        variable_names=["x3", "y1"],
        variable_names_to_group_names={
            "x3": IODataset.INPUT_GROUP,
            "y1": IODataset.OUTPUT_GROUP,
        },
    )

    point_2 = ValidationPointResult(
        nominal_data={
            "x1_vector": linspace(0, 1, 3),
            "x2": array([2.0]),
            "x3": 3.0,
            "x4": "bar",
        },
        measured_data=measured_data,
        simulated_data=simulated_data,
        integrated_metrics={
            "RelativeErrorMetric": {
                "y1": mean_metric.compute(measured_data, simulated_data)
            }
        },
    )
    point_2.metadata.settings["metric_names"] = ["RelativeErrorMetric"]
    point_2.metadata.report["measured_output_names"] = ["y1"]
    result = ValidationCaseResult()
    result.set_from_point_results([point_1, point_2])
    return result


@pytest.fixture
def deterministic_validation_case(reference_data):
    """A mock ValidationCase set from deterministic validation."""
    validation_case = DeterministicValidationCase()

    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    validation_case.execute(
        inputs=DeterministicValidationCaseInputs(
            model=model, reference_data=reference_data
        ),
        settings=DeterministicValidationCaseSettings(output_names=["y4"]),
    )
    return validation_case


@pytest.mark.parametrize(
    "metric_names",
    [
        ([]),
        ([
            "RelativeErrorMetric",
        ]),
    ],
)
def test_end_to_end_deterministic_validation(tmp_wd, reference_data, metric_names):
    """Check that a sample to sample validation point computes correct error value."""
    validation_case = DeterministicValidationCase()

    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    # TODO see how to manage nominal data for deterministic case
    settings = {"output_names": ["y4"]}
    if len(metric_names) > 0:
        settings.update({"metric_names": metric_names})

    validation_case.execute(
        inputs=DeterministicValidationCaseInputs(
            model=model, reference_data=reference_data
        ),
        settings=DeterministicValidationCaseSettings(**settings),
    )

    assert validation_case.result.element_wise_metrics.get_variable_names(
        IODataset.INPUT_GROUP
    ) == ["x1", "x2", "x3"]
    for name in metric_names:
        assert validation_case.result.element_wise_metrics.get_variable_names(name) == [
            "y4"
        ]

    assert_allclose(
        validation_case.result.element_wise_metrics
        .get_view(variable_names="y4", group_names="RelativeErrorMetric")
        .to_numpy()
        .ravel(),
        array([0.090909, 0.166667]),
        rtol=1e-5,
    )

    assert set(metric_names or validation_case.options["metric_names"]) == set(
        validation_case.result.integrated_metrics.keys()
    )

    assert validation_case.result.integrated_metrics["RelativeErrorMetric"][
        "y4"
    ] == pytest.approx(0.1287879)


def test_simulations_are_run_by_the_doe_subtool(tmp_wd, reference_data):
    """Check that the samples are simulated by the DOE subtool, once per cache file.

    The vector input ``x3`` of the reference data has two sizes, so the two samples
    are in two cache files and simulated by two executions of the DOE subtool.
    """
    archive_root = tmp_wd / "archive"
    validation_case = DeterministicValidationCase(
        archive_manager="DirectoryArchive", archive_root=archive_root
    )
    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    validation_case.execute(
        inputs=DeterministicValidationCaseInputs(
            model=model, reference_data=reference_data
        ),
        settings=DeterministicValidationCaseSettings(output_names=["y4"]),
    )

    # One archived run of the DOE subtool per cache file, child of the validation.
    runs = {
        run["tool_run_id"]: run
        for run in DirectoryToolArchive(archive_root).search_tool_runs()
    }
    child_ids = validation_case.result.metadata.child_tool_run_ids
    assert len(child_ids) == 2
    assert {runs[child_id]["tool_name"] for child_id in child_ids} == {"CustomDOETool"}
    assert all(len(runs[child_id]["simulation_run_ids"]) == 1 for child_id in child_ids)

    # The DOE subtool holds all the samples, in the order of the reference data.
    doe_result = validation_case._subtools["CustomDOETool"].result
    assert_allclose(
        doe_result.dataset.get_view(
            group_names=IODataset.INPUT_GROUP, variable_names=["x3", "x1", "x2"]
        ).to_numpy(),
        reference_data.get_view(
            group_names=IODataset.INPUT_GROUP, variable_names=["x3", "x1", "x2"]
        ).to_numpy(),
    )
    assert_allclose(
        doe_result.dataset.get_view(
            group_names=IODataset.OUTPUT_GROUP, variable_names="y4"
        ).to_numpy(),
        validation_case.result.element_wise_metrics.get_view(
            group_names=IODataset.OUTPUT_GROUP, variable_names="y4"
        ).to_numpy(),
    )
    assert set(doe_result.metadata.simulation_run_ids) == set(
        validation_case.result.metadata.simulation_run_ids
    )


def test_validation_plots(tmp_wd, deterministic_validation_case):
    """Check that validation plots are saved on disk."""
    directory = deterministic_validation_case.working_directory
    figures = deterministic_validation_case.result.visualize(
        directory_path=directory,
        metric_names=["RelativeErrorMetric"],
        output_names=["y4"],
        save=True,
    )
    expected_keys = [
        "error_scatter_matrix_RelativeErrorMetric_y4",
        "parallel_coordinates_RelativeErrorMetric_y4",
        "predict_vs_true_RelativeErrorMetric_y4",
        "integrated_metric_bars_RelativeErrorMetric",
    ]
    assert set(figures) == set(expected_keys)
    for key in expected_keys:
        assert (directory / f"{key}.html").is_file()


def test_to_dataframe(tmp_wd, stochastic_case_result):
    """Check that a ValidationCaseResult can export a DataFrame containing the
    nominal input variables, the simulated outputs, the reference outputs
    and the integrated metrics as outputs."""

    result = stochastic_case_result
    point_1 = result.stochastic_point_results[0]
    point_2 = result.stochastic_point_results[1]
    assert set(
        result.element_wise_metrics.get_variable_names(IODataset.INPUT_GROUP)
    ) == {"x3"}
    assert set(
        result.element_wise_metrics.get_variable_names(IODataset.OUTPUT_GROUP)
    ) == {"y1"}
    assert set(result.element_wise_metrics.get_variable_names("ReferenceInputs")) == {
        "x3"
    }
    assert set(result.element_wise_metrics.get_variable_names("ReferenceOutputs")) == {
        "y1"
    }
    # Expected value is the mean value of the input variable x3 for each point,
    # which is 2.0 for point_1 and 2.1 for point_2
    assert_allclose(
        result.element_wise_metrics
        .get_view(group_names="ReferenceInputs")
        .to_numpy()
        .ravel(),
        array([2.0, 2.1]),
    )
    assert_allclose(
        result.element_wise_metrics
        .get_view(group_names="ReferenceOutputs")
        .to_numpy()
        .ravel(),
        array([3.0, 3.1]),
    )
    assert_allclose(
        result.element_wise_metrics
        .get_view(group_names=IODataset.INPUT_GROUP)
        .to_numpy()
        .ravel(),
        array([2.5, 2.6]),
    )
    assert_allclose(
        result.element_wise_metrics
        .get_view(group_names=IODataset.OUTPUT_GROUP)
        .to_numpy()
        .ravel(),
        array([3.5, 3.6]),
    )
    assert_allclose(
        result.element_wise_metrics
        .get_view(group_names="RelativeErrorMetric")
        .to_numpy()
        .ravel(),
        array([
            point_1.integrated_metrics["RelativeErrorMetric"]["y1"],
            point_2.integrated_metrics["RelativeErrorMetric"]["y1"],
        ]),
    )
    assert set(result.integrated_metrics.keys()) == {"RelativeErrorMetric"}
    assert set(result.integrated_metrics["RelativeErrorMetric"].keys()) == {"y1"}
    assert result.integrated_metrics["RelativeErrorMetric"]["y1"] == pytest.approx(
        0.5
        * (
            point_1.integrated_metrics["RelativeErrorMetric"]["y1"]
            + point_2.integrated_metrics["RelativeErrorMetric"]["y1"]
        )
    )


def test_serialization_stochastic_result(tmp_wd, stochastic_case_result):
    """Check that a ValidationCaseResult obtained from stochastic validation points
    can be serialized to hdf5."""
    result = stochastic_case_result
    result.to_hdf5("result.hdf5")
    serialized_result = ValidationCaseResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)


def test_serialization_deterministic_result(tmp_wd, deterministic_validation_case):
    """Check that a ValidationCaseResult obtained from deterministic validation
    can be serialized to hdf5."""
    result = deterministic_validation_case.result
    result.to_hdf5("result.hdf5")
    serialized_result = ValidationCaseResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)


def test_result_visualization(tmp_wd, deterministic_validation_case):
    """Check that a validation case result can be visualized once loaded from a
    file."""
    check_result_visualization(deterministic_validation_case.result, "visualization")
    tables = deterministic_validation_case.result.tabulate()
    assert "integrated_metrics" in tables
    assert "element_wise_metrics" in tables


def test_key_values(tmp_wd, deterministic_validation_case):
    """The integrated metrics and the metrics of each point summarize a validation
    case."""
    result = deterministic_validation_case.result
    key_values = result.get_key_values()
    n_points = len(result.element_wise_metrics)
    for metric_name, values in result.integrated_metrics.items():
        for output_name, value in values.items():
            name = f"{metric_name}.{output_name}"
            assert key_values[name] == pytest.approx(value)
            point_values = result.element_wise_metrics.get_view(
                group_names=metric_name, variable_names=output_name
            ).to_numpy()[:, 0]
            assert [
                key_values[f"{name}.point_{i}"] for i in range(n_points)
            ] == pytest.approx(point_values)
