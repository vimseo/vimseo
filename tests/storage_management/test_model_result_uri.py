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

"""Tests of the references of the model results."""

from __future__ import annotations

import pytest
from numpy import atleast_1d

from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNode
from vimseo.api import load_analysis_node_results
from vimseo.api import load_model_results
from vimseo.api import search_analysis_node_runs
from vimseo.api import search_model_results
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel

pytestmark = pytest.mark.fast


@pytest.fixture(params=["DirectoryArchive", "MlflowArchive"])
def archive(request, tmp_wd):
    if request.param == "MlflowArchive":
        pytest.importorskip("mlflow")
    archive = {
        "archive_manager": request.param,
        "directory_archive_root": tmp_wd / "archive",
    }
    model = MockModel("LC1", **archive)
    model.cache = None
    model.execute({"x1": atleast_1d(0.5)})
    MyAnalysisNode(**archive).execute()
    return archive


def test_references_of_a_simulation(archive):
    """A simulation is loaded from its uri, its run_id, with or without scheme."""
    (summary,) = search_model_results(**archive)
    run_id = summary["run_id"]
    for reference in (summary["uri"], run_id, f"run:{run_id}"):
        (result,) = load_model_results(reference, **archive)
        assert result.run_id == run_id
        assert result.scalars["x1"] == pytest.approx(0.5)


def test_unknown_run_id(archive):
    with pytest.raises(KeyError, match="No simulation"):
        load_model_results("run:20000101T000000_00000000", **archive)


def test_references_of_the_wrong_kind(archive):
    """A reference of the other kind of result raises an error naming the function."""
    (simulation,) = search_model_results(**archive)
    (analysis_node_run,) = search_analysis_node_runs(**archive)
    with pytest.raises(ValueError, match="load_analysis_node_results"):
        load_model_results(analysis_node_run["uri"], **archive)
    with pytest.raises(ValueError, match="load_model_results"):
        load_analysis_node_results(simulation["uri"], **archive)
    with pytest.raises(ValueError, match="load_analysis_node_results"):
        load_model_results(
            f"analysis-node-run:{analysis_node_run['analysis_node_run_id']}", **archive
        )
    with pytest.raises(ValueError, match="load_model_results"):
        load_analysis_node_results(f"run:{simulation['run_id']}", **archive)
