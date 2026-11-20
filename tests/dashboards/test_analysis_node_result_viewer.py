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

"""Tests of the dashboard exploring any analysis node result."""

from __future__ import annotations

from itertools import count
from pathlib import Path
from unittest import mock

import pytest
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from numpy import full
from pandas import DataFrame
from streamlit.testing.v1 import AppTest

import vimseo.dashboards.analysis_node_result.analysis_node_result_viewer as viewer
import vimseo.dashboards.main_dashboard as main_dashboard
from vimseo.analysis_nodes.doe.custom_doe import CustomDOEAnalysisNode
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.api import create_model
from vimseo.dashboards.visualisation.result_loader import ResultSource
from vimseo.dashboards.visualisation.result_view import filter_columns
from vimseo.dashboards.visualisation.result_view import group_columns_by_variable

TIMEOUT = 300

ARCHIVE = "archive"

PAGE = Path(main_dashboard.__file__).parent / "pages" / "1_AnalysisNodeResults.py"
"""The page exploring any analysis node result."""


def execute_doe(archive_manager: str) -> CustomDOEAnalysisNode:
    """Execute a DOE varying an input of a model with curves, archived and saved in a
    file."""
    input_dataset = IODataset()
    input_dataset.add_variable("x", array([[1.0], [2.0], [3.0]]), IODataset.INPUT_GROUP)
    input_dataset.add_variable("x_1", full((3, 1), 0.5), IODataset.INPUT_GROUP)
    analysis_node = CustomDOEAnalysisNode(
        archive_manager=archive_manager, directory_archive_root=ARCHIVE
    )
    # The CPU time, the only scalar output, must vary to draw the scatter matrix,
    # whereas a run can be shorter than the resolution of the clock, e.g. 16 ms under
    # Windows: the runs last 1, 5 and 9 seconds.
    clock = (float(i**2) for i in count())
    with mock.patch(
        "vimseo.core.base_integrated_model.time", side_effect=lambda: next(clock)
    ):
        analysis_node.execute(
            model=create_model("MockCurves", "Dummy"), input_dataset=input_dataset
        )
    analysis_node.save_results()
    return analysis_node


@pytest.fixture
def doe_analysis_node(tmp_wd) -> CustomDOEAnalysisNode:
    """A DOE archived in a directory."""
    return execute_doe("DirectoryArchive")


@pytest.fixture
def space_analysis_node(tmp_wd) -> SpaceAnalysisNode:
    """A space analysis node, whose result is explored in a specific dashboard."""
    analysis_node = SpaceAnalysisNode(
        archive_manager="DirectoryArchive", directory_archive_root=ARCHIVE
    )
    analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    analysis_node.save_results()
    return analysis_node


@pytest.fixture
def app() -> AppTest:
    app = AppTest.from_file(str(PAGE), default_timeout=TIMEOUT)
    app.run()
    assert not app.exception
    return app


def check_doe_result_is_shown(app: AppTest) -> None:
    assert not app.exception
    assert any("DOEResult" in markdown.value for markdown in app.markdown)
    # The dataset and the settings of the analysis node.
    assert len(app.dataframe) >= 2
    figure_names = app.multiselect(
        key="analysis_node_result_viewer_figure_names"
    ).options
    assert "scatter_matrix" in figure_names
    assert "scalar_outputs_vs_x" in figure_names
    assert "curves_y_history_vs_x_history" in figure_names
    assert any("along `x`: 1 family" in info.value for info in app.info)


def test_without_result(app):
    assert any("Load an analysis node result" in info.value for info in app.info)


def test_from_directory_archive(app, doe_analysis_node, space_analysis_node):
    """The runs of all the analysis nodes are listed, whatever their results."""
    app.sidebar.radio[0].set_value(ResultSource.ARCHIVE).run()
    app.selectbox(key="analysis_node_result_viewer_archive_manager").set_value(
        "DirectoryArchive"
    ).run()
    app.text_input(key="analysis_node_result_viewer_archive_root").set_value(
        ARCHIVE
    ).run()
    assert app.selectbox(
        key="analysis_node_result_viewer_analysis_node_name"
    ).options == [
        "All analysis nodes",
        "CustomDOEAnalysisNode",
        "SpaceAnalysisNode",
    ]
    app.selectbox(key="analysis_node_result_viewer_analysis_node_name").set_value(
        "CustomDOEAnalysisNode"
    ).run()
    check_doe_result_is_shown(app)


def test_from_mlflow_archive(app, tmp_wd):
    """An analysis node result is loaded from an MLflow archive."""
    pytest.importorskip("mlflow")
    execute_doe("MlflowArchive")
    app.sidebar.radio[0].set_value(ResultSource.ARCHIVE).run()
    app.selectbox(key="analysis_node_result_viewer_archive_manager").set_value(
        "MlflowArchive"
    ).run()
    app.text_input(key="analysis_node_result_viewer_archive_root").set_value(
        ARCHIVE
    ).run()
    check_doe_result_is_shown(app)


def test_from_uri(app, doe_analysis_node):
    app.sidebar.radio[0].set_value(ResultSource.URI).run()
    uri = str(doe_analysis_node.working_directory / "CustomDOEAnalysisNode_result.hdf5")
    app.sidebar.text_input[0].set_value(uri).run()
    check_doe_result_is_shown(app)


def test_space_result(app, space_analysis_node):
    """A space analysis node result is explored like any analysis node result."""
    app.sidebar.radio[0].set_value(ResultSource.URI).run()
    uri = str(space_analysis_node.working_directory / "SpaceAnalysisNode_result.hdf5")
    app.sidebar.text_input[0].set_value(uri).run()
    assert not app.exception
    assert any("SpaceAnalysisNodeResult" in markdown.value for markdown in app.markdown)
    assert app.tabs


def test_from_unknown_mlflow_run(app, tmp_wd):
    pytest.importorskip("mlflow")
    app.sidebar.radio[0].set_value(ResultSource.URI).run()
    app.sidebar.text_input[0].set_value("runs:/123").run()
    assert not app.exception
    assert "No MLflow run" in app.sidebar.error[0].value


def test_scatter_matrix_variable_names(app, doe_analysis_node):
    """The variables of the scatter matrix of a DOE can be selected."""
    app.sidebar.radio[0].set_value(ResultSource.URI).run()
    uri = str(doe_analysis_node.working_directory / "CustomDOEAnalysisNode_result.hdf5")
    app.sidebar.text_input[0].set_value(uri).run()
    selector = app.multiselect(
        key="analysis_node_result_viewer_scatter_matrix_variable_names"
    )
    assert selector.options == ["x", "x_1", "cpu_time"]
    selector.set_value(["x", "cpu_time"]).run()
    assert not app.exception


def test_filter_the_columns_of_a_table(app, doe_analysis_node):
    """The vectors of the dataset are left out by default and its variables can be
    selected."""
    app.sidebar.radio[0].set_value(ResultSource.URI).run()
    uri = str(doe_analysis_node.working_directory / "CustomDOEAnalysisNode_result.hdf5")
    app.sidebar.text_input[0].set_value(uri).run()

    def get_columns() -> list[str]:
        return list(app.dataframe[0].value.columns)

    assert "x" in get_columns()
    assert not any(column.startswith("y_history[") for column in get_columns())

    app.checkbox(key="analysis_node_result_viewer_dataset_scalars_only").uncheck().run()
    assert "y_history[0]" in get_columns()

    app.multiselect(key="analysis_node_result_viewer_dataset_variables").set_value([
        "x",
        "y_history",
    ]).run()
    assert not app.exception
    columns = get_columns()
    assert columns[0] == "x"
    assert all(column.startswith("y_history[") for column in columns[1:])


def test_group_columns_by_variable():
    table = DataFrame(columns=["x", "y[0]", "y[1]", "date"])
    assert group_columns_by_variable(table) == {
        "x": ["x"],
        "y": ["y[0]", "y[1]"],
        "date": ["date"],
    }


def test_filter_columns():
    table = DataFrame([[1.0, 2.0, 3.0, "d"]], columns=["x", "y[0]", "y[1]", "date"])
    assert list(filter_columns(table)) == ["x", "y[0]", "y[1]", "date"]
    assert list(filter_columns(table, scalars_only=True)) == ["x", "date"]
    assert list(filter_columns(table, ["y"])) == ["y[0]", "y[1]"]
    assert list(filter_columns(table, ["x", "y"], scalars_only=True)) == ["x"]


def test_describe_families():
    """The families of a DOE are listed along each input forming some."""
    description = viewer.describe_families({
        "x": {"x_1=0.5": [0, 1, 2], "x_1=1.0": [3, 4, 5]},
        "x_1": {"": [0, 1]},
    })
    assert (
        "- along `x`: 2 families, x_1=0.5 (3 samples), x_1=1.0 (3 samples)"
        in description
    )
    assert "- along `x_1`: 1 family of 2 samples, the only varying input" in (
        description
    )


def test_describe_many_families():
    """Only the first families are listed."""
    description = viewer.describe_families({
        "x": {f"x_1={i}": [2 * i, 2 * i + 1] for i in range(7)}
    })
    assert "7 families" in description
    assert "x_1=4 (2 samples), ..." in description
    assert "x_1=5" not in description


def test_describe_no_family():
    assert "No family of samples varying a single input" in (
        viewer.describe_families({})
    )
