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

"""Tests of the view of a validation case in the page exploring the analysis node results."""

from __future__ import annotations

from pathlib import Path

import pytest
from gemseo.datasets.io_dataset import IODataset

import vimseo.dashboards.main_dashboard as main_dashboard
from vimseo.analysis_nodes.io.reader_file_dataframe import ReaderFileDataFrame
from vimseo.analysis_nodes.io.reader_file_dataframe import ReaderFileDataFrameSettings
from vimseo.analysis_nodes.validation_case.validation_case import (
    DeterministicValidationCase,
)
from vimseo.analysis_nodes.validation_case.validation_case import (
    DeterministicValidationCaseInputs,
)
from vimseo.analysis_nodes.validation_case.validation_case import (
    DeterministicValidationCaseSettings,
)
from vimseo.api import create_model
from vimseo.dashboards.visualisation.result_loader import ResultSource
from vimseo.problems.mock.mock_reference_data import MOCK_REFERENCE_DIR
from vimseo.utilities.test_utils import run_dashboard


@pytest.fixture
def validation_case_path(tmp_wd) -> Path:
    """The file of a deterministic validation case of a mock model."""
    reference_data = (
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
                variable_names_to_n_components={"x3": 3},
            ),
        )
        .dataset
    )
    analysis_node = DeterministicValidationCase()
    analysis_node.execute(
        inputs=DeterministicValidationCaseInputs(
            model=create_model("MockModelPersistent", "LC1"),
            reference_data=reference_data,
        ),
        settings=DeterministicValidationCaseSettings(output_names=["y4"]),
    )
    analysis_node.save_results()
    return analysis_node.working_directory / "DeterministicValidationCase_result.hdf5"


def test_explore_a_validation_case(validation_case_path):
    """A validation case is loaded, and its metrics and plots are browsed."""
    app = run_dashboard(
        Path(main_dashboard.__file__).parent / "pages" / "1_AnalysisNodeResults.py"
    )
    app.radio(key="analysis_node_result_viewer_source").set_value(
        ResultSource.URI
    ).run()
    app.text_input(key="analysis_node_result_viewer_uri").set_value(
        str(validation_case_path)
    ).run()
    assert not app.exception
    assert not app.error

    metric_selector = next(
        selectbox for selectbox in app.selectbox if selectbox.label == "Select a metric"
    )
    plot_selector = next(
        selectbox
        for selectbox in app.selectbox
        if selectbox.label == "Select of case validation plot"
    )
    for metric_name in metric_selector.options:
        metric_selector.set_value(metric_name).run()
        for plot_name in plot_selector.options:
            plot_selector.set_value(plot_name).run()
            assert not app.exception, (metric_name, plot_name)
