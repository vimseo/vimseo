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

"""Tests of the loading of an analysis node result from a URI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.analysis_nodes.space.space_analysis_node_result import (
    SpaceAnalysisNodeResult,
)
from vimseo.storage_management.analysis_node_archive import open_analysis_node_archive
from vimseo.storage_management.analysis_node_archive.directory_analysis_node_archive import (
    DirectoryAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.uri import (
    get_default_archive_manager,
)
from vimseo.storage_management.analysis_node_archive.uri import guess_archive_manager
from vimseo.storage_management.analysis_node_archive.uri import (
    load_analysis_node_result,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def directory_archive_root(tmp_wd) -> Path:
    return tmp_wd / "analysis_node_archive"


@pytest.fixture
def space_analysis_node(directory_archive_root) -> SpaceAnalysisNode:
    """A space analysis node whose result is archived in a directory."""
    analysis_node = SpaceAnalysisNode(
        archive_manager="DirectoryArchive",
        directory_archive_root=directory_archive_root,
    )
    analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    return analysis_node


def test_load_from_result_file(space_analysis_node):
    space_analysis_node.save_results()
    path = space_analysis_node.working_directory / "SpaceAnalysisNode_result.hdf5"
    for uri in (path, str(path)):
        result = load_analysis_node_result(uri)
        assert isinstance(result, SpaceAnalysisNodeResult)
        assert (
            result.metadata.analysis_node_run_id
            == space_analysis_node.result.metadata.analysis_node_run_id
        )


def test_load_from_run_directory(space_analysis_node, directory_archive_root):
    (summary,) = DirectoryAnalysisNodeArchive(
        directory_archive_root
    ).search_analysis_node_runs("SpaceAnalysisNode")
    result = load_analysis_node_result(summary["directory"])
    assert (
        result.metadata.analysis_node_run_id
        == space_analysis_node.result.metadata.analysis_node_run_id
    )


def test_load_from_analysis_node_run_id(space_analysis_node, directory_archive_root):
    run_id = space_analysis_node.result.metadata.analysis_node_run_id
    result = load_analysis_node_result(
        f"analysis-node-run:{run_id}", directory_archive_root=directory_archive_root
    )
    assert isinstance(result, SpaceAnalysisNodeResult)
    assert result.metadata.analysis_node_run_id == run_id


def test_load_from_unknown_analysis_node_run_id(
    space_analysis_node, directory_archive_root
):
    with pytest.raises(KeyError, match="No archived analysis node run foo"):
        load_analysis_node_result(
            "analysis-node-run:foo", directory_archive_root=directory_archive_root
        )


def test_load_from_mlflow_run(tmp_wd):
    """An analysis node result is loaded from the id of its MLflow run."""
    pytest.importorskip("mlflow")
    analysis_node = SpaceAnalysisNode(
        archive_manager="MlflowArchive", directory_archive_root="mlflow"
    )
    analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    (summary,) = open_analysis_node_archive(
        "MlflowArchive", "mlflow"
    ).search_analysis_node_runs()
    result = load_analysis_node_result(summary["uri"], directory_archive_root="mlflow")
    assert (
        result.metadata.analysis_node_run_id
        == analysis_node.result.metadata.analysis_node_run_id
    )


def test_load_from_unknown_mlflow_run(tmp_wd):
    pytest.importorskip("mlflow")
    with pytest.raises(KeyError, match="No MLflow run"):
        load_analysis_node_result("runs:/0123456789", directory_archive_root="mlflow")


def test_load_from_unsupported_scheme():
    with pytest.raises(ValueError, match="Unsupported scheme 'foo'"):
        load_analysis_node_result("foo:bar")


def test_load_from_missing_path(tmp_wd):
    with pytest.raises(FileNotFoundError, match="No analysis node result at"):
        load_analysis_node_result("missing.hdf5")


def test_load_from_directory_without_result(tmp_wd):
    directory = tmp_wd / "analysis_nodes" / "SpaceAnalysisNode" / "run"
    directory.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="does not contain the result file"):
        load_analysis_node_result(directory)


def test_load_from_analysis_node_run_id_in_mlflow(tmp_wd):
    """The manager of the archive of analysis-node-run:{analysis_node_run_id} is guessed from its root
    directory, or given explicitly."""
    pytest.importorskip("mlflow")
    analysis_node = SpaceAnalysisNode(
        archive_manager="MlflowArchive", directory_archive_root="mlflow"
    )
    analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    analysis_node_run_id = analysis_node.result.metadata.analysis_node_run_id
    uri = f"analysis-node-run:{analysis_node_run_id}"
    for manager in ("", "MlflowArchive"):
        result = load_analysis_node_result(
            uri, directory_archive_root="mlflow", archive_manager=manager
        )
        assert result.metadata.analysis_node_run_id == analysis_node_run_id


@pytest.mark.parametrize(
    ("content", "expected"),
    [("analysis_nodes", "DirectoryArchive"), ("0/meta.yaml", "MlflowArchive")],
)
def test_guess_archive_manager(tmp_wd, content, expected):
    path = tmp_wd / "root" / content
    path.parent.mkdir(parents=True)
    if content == "analysis_nodes":
        path.mkdir()
    else:
        path.touch()
    assert guess_archive_manager(tmp_wd / "root") == expected


def test_guess_archive_manager_from_configuration(tmp_wd):
    """Without known content, the archive manager is the one of the configuration."""
    assert guess_archive_manager(tmp_wd) == get_default_archive_manager()
