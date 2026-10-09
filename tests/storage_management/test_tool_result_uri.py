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

"""Tests of the loading of a tool result from a URI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from vimseo.api import load_tool_result
from vimseo.storage_management.tool_archive import open_tool_archive
from vimseo.storage_management.tool_archive.directory_tool_archive import (
    DirectoryToolArchive,
)
from vimseo.storage_management.tool_archive.uri import get_default_archive_manager
from vimseo.storage_management.tool_archive.uri import guess_archive_manager
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.tools.space.space_tool_result import SpaceToolResult

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def archive_root(tmp_wd) -> Path:
    return tmp_wd / "tool_archive"


@pytest.fixture
def space_tool(archive_root) -> SpaceTool:
    """A space tool whose result is archived in a directory."""
    tool = SpaceTool(archive_manager="DirectoryArchive", archive_root=archive_root)
    tool.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    return tool


def test_load_from_result_file(space_tool):
    space_tool.save_results()
    path = space_tool.working_directory / "SpaceTool_result.hdf5"
    for uri in (path, str(path)):
        result = load_tool_result(uri)
        assert isinstance(result, SpaceToolResult)
        assert result.metadata.tool_run_id == space_tool.result.metadata.tool_run_id


def test_load_from_run_directory(space_tool, archive_root):
    (summary,) = DirectoryToolArchive(archive_root).search_tool_runs("SpaceTool")
    result = load_tool_result(summary["directory"])
    assert result.metadata.tool_run_id == space_tool.result.metadata.tool_run_id


def test_load_from_tool_run_id(space_tool, archive_root):
    run_id = space_tool.result.metadata.tool_run_id
    result = load_tool_result(f"tool-run:{run_id}", archive_root=archive_root)
    assert isinstance(result, SpaceToolResult)
    assert result.metadata.tool_run_id == run_id


def test_load_from_unknown_tool_run_id(space_tool, archive_root):
    with pytest.raises(KeyError, match="No archived tool run foo"):
        load_tool_result("tool-run:foo", archive_root=archive_root)


def test_load_from_mlflow_run(tmp_wd):
    """A tool result is loaded from the id of its MLflow run."""
    pytest.importorskip("mlflow")
    tool = SpaceTool(archive_manager="MlflowArchive", archive_root="mlflow")
    tool.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    (summary,) = open_tool_archive("MlflowArchive", "mlflow").search_tool_runs()
    result = load_tool_result(summary["uri"], archive_root="mlflow")
    assert result.metadata.tool_run_id == tool.result.metadata.tool_run_id


def test_load_from_unknown_mlflow_run(tmp_wd):
    pytest.importorskip("mlflow")
    with pytest.raises(KeyError, match="No MLflow run"):
        load_tool_result("runs:/0123456789", archive_root="mlflow")


def test_load_from_unsupported_scheme():
    with pytest.raises(ValueError, match="Unsupported scheme 'foo'"):
        load_tool_result("foo:bar")


def test_load_from_missing_path(tmp_wd):
    with pytest.raises(FileNotFoundError, match="No tool result at"):
        load_tool_result("missing.hdf5")


def test_load_from_directory_without_result(tmp_wd):
    directory = tmp_wd / "tools" / "SpaceTool" / "run"
    directory.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="does not contain the result file"):
        load_tool_result(directory)


def test_load_from_tool_run_id_in_mlflow(tmp_wd):
    """The manager of the archive of tool-run:{tool_run_id} is guessed from its root
    directory, or given explicitly."""
    pytest.importorskip("mlflow")
    tool = SpaceTool(archive_manager="MlflowArchive", archive_root="mlflow")
    tool.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    tool_run_id = tool.result.metadata.tool_run_id
    uri = f"tool-run:{tool_run_id}"
    for manager in ("", "MlflowArchive"):
        result = load_tool_result(uri, archive_root="mlflow", archive_manager=manager)
        assert result.metadata.tool_run_id == tool_run_id


@pytest.mark.parametrize(
    ("content", "expected"),
    [("tools", "DirectoryArchive"), ("0/meta.yaml", "MlflowArchive")],
)
def test_guess_archive_manager(tmp_wd, content, expected):
    path = tmp_wd / "root" / content
    path.parent.mkdir(parents=True)
    if content == "tools":
        path.mkdir()
    else:
        path.touch()
    assert guess_archive_manager(tmp_wd / "root") == expected


def test_guess_archive_manager_from_configuration(tmp_wd):
    """Without known content, the archive manager is the one of the configuration."""
    assert guess_archive_manager(tmp_wd) == get_default_archive_manager()
