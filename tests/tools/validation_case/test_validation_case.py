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
from numpy import array
from numpy import linspace
from numpy.testing import assert_allclose

from vimseo.api import create_model
from vimseo.problems.mock.mock_reference_data import MOCK_REFERENCE_DIR
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
from vimseo.tools.validation_case.validation_case_result import (
    DeterministicValidationCaseResult,
)


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


def test_validation_plots(tmp_wd, reference_data):
    """Check that validation plots are saved on disk."""
    validation_case = DeterministicValidationCase()

    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    validation_case.execute(
        inputs=DeterministicValidationCaseInputs(
            model=model, reference_data=reference_data
        ),
        settings=DeterministicValidationCaseSettings(output_names=["y4"]),
    )
    validation_case.plot_results(
        validation_case.result,
        "RelativeErrorMetric",
        "y4",
        save=True,
        show=False,
    )
    assert (
        validation_case.working_directory
        / "error_scatter_matrix_RelativeErrorMetric_y4.html"
    ).is_file()
    assert (
        validation_case.working_directory
        / "parallel_coordinates_RelativeErrorMetric_y4.html"
    ).is_file()
    assert (
        validation_case.working_directory
        / "metric_histogram_RelativeErrorMetric_y4.html"
    ).is_file()
    assert (validation_case.working_directory / "integrated_metric_bars.html").is_file()


# TODO wait for refactoring of validaiton case tool
def test_to_dataframe(tmp_wd):
    """Check that a StochasticValidationCaseResult can export a DataFrame containing the
    nominal input variables and the integrated metrics as outputs."""
    point_1 = ValidationPointResult(
        nominal_data={
            "x1_vector": linspace(0, 1, 5),
            "x2": array([1.0]),
            "x3": 2.0,
            "x4": "foo",
        },
        # TODO add a vector to the measured data
        measured_data=IODataset.from_array(
            [[1, 2], [1.5, 2.5]],
            variable_names=["x3", "y1"],
            variable_names_to_group_names={
                "x3": IODataset.INPUT_GROUP,
                "y1": IODataset.OUTPUT_GROUP,
            },
        ),
        integrated_metrics={"metric1": {"y1": 3.0}},
    )
    point_2 = ValidationPointResult(
        nominal_data={
            "x1_vector": linspace(0, 1, 3),
            "x2": array([2.0]),
            "x3": 3.0,
            "x4": "bar",
        },
        measured_data=IODataset.from_array(
            [[1, 2], [1.5, 2.5]],
            variable_names=["x3", "y1"],
            variable_names_to_group_names={
                "x3": IODataset.INPUT_GROUP,
                "y1": IODataset.OUTPUT_GROUP,
            },
        ),
        integrated_metrics={"metric1": {"y1": 4.0}},
    )
    result = DeterministicValidationCaseResult()
    result.set_from_point_results([point_1, point_2])
    # df = result.to_dataframe("metric1")
    # assert list(df["x1_vector"].values) == [
    #     "[0.   0.25 0.5  0.75 1.  ]",
    #     "[0.  0.5 1. ]",
    # ]
    # assert df.shape == (2, 5)
    # assert list(df.columns.values) == ["x1_vector", "x2", "x3", "x4", "metric1[y1]"]
