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

"""Tests of the collections of results and of the data management API."""

from __future__ import annotations

import pytest
from numpy import atleast_1d

from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNode
from vimseo.analysis_nodes.mock.mock_analysis_node import MyBaseCompositeAnalysisNode
from vimseo.api import create_model
from vimseo.api import load_analysis_node_results
from vimseo.api import load_model_results
from vimseo.api import open_analysis_node_results
from vimseo.api import open_model_results
from vimseo.api import search_analysis_node_runs
from vimseo.api import search_model_results
from vimseo.results.collection import AnalysisNodeResults
from vimseo.results.collection import Families
from vimseo.results.collection import FamilyKey
from vimseo.results.collection import ModelResults

pytestmark = pytest.mark.fast

HEIGHTS = (30.0, 40.0, 50.0)
WIDTHS = (20.0, 30.0)


def _execute(archive, monkeypatch=None):
    """Archive a grid of simulations, a duplicate and a failed one."""
    model = create_model("BendingTestAnalytical", "Cantilever", **archive)
    model.cache = None
    for width in WIDTHS:
        for height in HEIGHTS:
            model.execute({
                "height": atleast_1d(height),
                "width": atleast_1d(width),
                "imposed_dplt": atleast_1d(-5.0),
            })
    # A duplicate, whose numerical setting differs.
    model.execute({
        "height": atleast_1d(40.0),
        "width": atleast_1d(20.0),
        "relative_dplt_location": atleast_1d(1.0),
    })
    return model


@pytest.fixture(params=["DirectoryArchive", "MlflowArchive"])
def archive(request, tmp_wd):
    if request.param == "MlflowArchive":
        pytest.importorskip("mlflow")
    archive = {
        "archive_manager": request.param,
        "directory_archive_root": tmp_wd / "archive",
        "study_name": "convergence",
    }
    _execute(archive)
    return archive


def test_open_and_filter(archive):
    """A collection is opened from the archive and filtered without mutation."""
    model_results = open_model_results(**archive)
    assert isinstance(model_results, ModelResults)
    assert len(model_results) == 7
    assert "7 model results" in repr(model_results)

    selected = model_results.filter(
        query="`inputs.height` < 35 or `inputs.width` > 25", failed=False
    )
    assert len(selected) == 4
    assert len(model_results) == 7
    assert set(selected.to_dataframe(["height"])["height"]) == {30.0, 40.0, 50.0}
    assert len(model_results.filter(model_name="BendingTestAnalytical")) == 7
    assert len(model_results.filter(failed=True)) == 0

    result = selected[0]
    assert result.run_id == selected.summaries["run_id"][0]
    assert result.plots.names


def test_ignoring_varying_inputs_and_duplicates(archive):
    """An ignored input stays in the results but is left out of the comparisons."""
    model_results = open_model_results(**archive)
    assert set(model_results.varying_inputs().index) == {"height", "width"}
    duplicates = model_results.duplicates()
    assert len(duplicates) == 2
    assert set(duplicates["group"]) == {0}

    ignoring = model_results.ignoring("width")
    assert ignoring.ignored == ("width",)
    assert set(ignoring.varying_inputs().index) == {"height"}
    assert "width" in ignoring.to_dataframe().columns


def test_families(archive):
    """The results differing by one input are grouped in families."""
    families = open_model_results(**archive).families(along="height")
    assert isinstance(families, Families)
    assert len(families) == 2
    assert families.along == "height"
    family = families.get(width=20.0)
    assert list(family.summaries["inputs.height"]) == [30.0, 40.0, 40.0, 50.0]
    assert families[FamilyKey((("width", 30.0),))] is not None
    assert families.get(width=99.0) is None
    figures = families.visualize()
    assert "scalar_outputs_vs_height[width=20.0]" in figures
    assert "curves_dplt_vs_dplt_grid[width=30.0]" in figures
    assert set(families.to_dataframe()["family"]) == {"width=20.0", "width=30.0"}


def test_plot_a_collection(archive):
    """The curves of the results are superposed, labelled by the varying inputs."""
    model_results = open_model_results(**archive).filter("`inputs.width` == 30")
    figures = model_results.visualize()
    assert set(figures) == {"dplt_vs_dplt_grid", "moment_vs_moment_grid"}
    assert len(figures["dplt_vs_dplt_grid"].data) == 3


def test_plot_a_figure_missing_from_some_results(tmp_wd, caplog):
    """A figure missing from some results is not drawn, with a warning."""
    archive = {"archive_manager": "DirectoryArchive", "directory_archive_root": "a"}
    create_model("BendingTestAnalytical", "Cantilever", **archive).execute()
    create_model("MockMultiCurves", "Dummy", **archive).execute()
    model_results = open_model_results(**archive)
    figures = model_results.visualize(
        plot_names=["dplt_vs_dplt_grid", "crack_propagation"]
    )
    assert figures == {}
    assert "['dplt_vs_dplt_grid', 'crack_propagation'] are not drawn" in caplog.text


def test_search_and_load(archive):
    """A summary gives the uri of its result; load_model_results takes one or many."""
    summaries = search_model_results(**archive, query="`inputs.height` == 50")
    assert len(summaries) == 2
    assert summaries[0]["study_name"] == "convergence"
    assert summaries[0]["run_id"] < summaries[1]["run_id"]

    loaded = load_model_results(summaries[0]["uri"], **archive)
    assert isinstance(loaded, ModelResults)
    assert loaded[0].run_id == summaries[0]["run_id"]

    run_ids = [summary["run_id"] for summary in reversed(summaries)]
    loaded = load_model_results(run_ids, **archive)
    assert [result.run_id for result in loaded] == run_ids
    loaded = load_model_results([f"run:{run_id}" for run_id in run_ids], **archive)
    assert [result.run_id for result in loaded] == run_ids


def test_analysis_node_results(tmp_wd):
    """The analysis node results are a collection too, compared on their settings."""
    archive = {
        "archive_manager": "DirectoryArchive",
        "directory_archive_root": tmp_wd / "archive",
        "study_name": "analysis_nodes",
    }
    for foo in ("a", "b"):
        MyAnalysisNode(**archive).execute(foo=foo)
    analysis_node_results = open_analysis_node_results(**archive)
    assert isinstance(analysis_node_results, AnalysisNodeResults)
    assert len(analysis_node_results) == 2
    assert "foo" in analysis_node_results.varying_inputs().index

    analysis_node_run_id = analysis_node_results.summaries["analysis_node_run_id"][0]
    loaded = load_analysis_node_results(analysis_node_run_id, **archive)
    assert loaded[0].metadata.analysis_node_run_id == analysis_node_run_id
    assert len(search_analysis_node_runs(**archive, query="`inputs.foo` == 'b'")) == 1


def test_analysis_node_results_children(tmp_wd):
    """The results of the sub-analysis nodes of a run are loaded from the archive."""
    archive = {
        "archive_manager": "DirectoryArchive",
        "directory_archive_root": tmp_wd / "archive",
    }
    sub_analysis_node = MyAnalysisNode()
    composite = MyBaseCompositeAnalysisNode(
        sub_analysis_nodes=[sub_analysis_node], **archive
    )
    composite.execute()

    children = open_analysis_node_results(**archive).children(
        composite.result.metadata.analysis_node_run_id
    )
    sub_run_id = sub_analysis_node.result.metadata.analysis_node_run_id
    assert list(children.summaries["analysis_node_run_id"]) == [sub_run_id]
    assert children[0].metadata.analysis_node_run_id == sub_run_id


def _create_analysis_node_results() -> AnalysisNodeResults:
    """Create the analysis node results of an archive holding a DOE and a design value."""
    from pandas import DataFrame

    return AnalysisNodeResults(
        DataFrame([
            {
                "analysis_node_run_id": "doe",
                "analysis_node_name": "DOEAnalysisNode",
                "status": "FINISHED",
                "inputs.n_samples": 10,
                "outputs.n_samples": 10.0,
            },
            {
                "analysis_node_run_id": "design_value",
                "analysis_node_name": "DesignValueAnalysisNode",
                "status": "FINISHED",
                "inputs.n_samples": 10,
                "outputs.mean": 1.0,
            },
        ]),
        loader=lambda row: None,
    )


def test_analysis_node_results_of_one_analysis_node_have_its_columns_only():
    """The columns of the other analysis nodes are dropped from the results of one analysis node."""
    analysis_node_results = _create_analysis_node_results()
    assert "outputs.mean" in analysis_node_results.summaries.columns
    design_values = analysis_node_results.filter(
        analysis_node_name="DesignValueAnalysisNode"
    )
    assert "outputs.n_samples" not in design_values.summaries.columns
    assert list(design_values.to_dataframe().columns[-2:]) == ["n_samples", "mean"]
    assert (
        "outputs.mean"
        not in analysis_node_results.filter(
            analysis_node_name="DOEAnalysisNode"
        ).summaries
    )


def test_to_dataframe_keeps_the_prefixes_of_homonyms():
    """An input and an output with the same name keep their prefixes."""
    table = (
        _create_analysis_node_results()
        .filter(analysis_node_name="DOEAnalysisNode")
        .to_dataframe()
    )
    assert {"inputs.n_samples", "outputs.n_samples"} <= set(table.columns)
    assert "n_samples" not in table.columns


def test_analysis_node_results_of_several_analysis_nodes(tmp_wd):
    """Comparing the results of several analysis nodes raises an error."""
    from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNodeNoInputs

    archive = {
        "archive_manager": "DirectoryArchive",
        "directory_archive_root": tmp_wd / "archive",
    }
    MyAnalysisNode(**archive).execute()
    MyAnalysisNodeNoInputs(**archive).execute()
    with pytest.raises(ValueError, match="filter\\(analysis_node_name"):
        open_analysis_node_results(**archive).varying_inputs()
    assert (
        len(
            open_analysis_node_results(**archive).filter(
                analysis_node_name="MyAnalysisNode"
            )
        )
        == 1
    )
