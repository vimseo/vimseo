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

"""Tests of the command line visualizing tool results."""

from __future__ import annotations

import json

import pytest

from vimseo.tools.space.space_tool import SpaceTool
from vimseo.tools.visualize_tool_result import main
from vimseo.tools.visualize_tool_result import parse_options


@pytest.fixture
def space_tool(tmp_wd) -> SpaceTool:
    """A space tool whose result is archived in a directory."""
    tool = SpaceTool(archive_manager="DirectoryArchive", archive_root="archive")
    tool.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromCenterAndCov",
        center_values={"x": 0.5, "y": 1.0},
        cov=0.05,
    )
    tool.save_results()
    return tool


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ([], {}),
        (["n=3"], {"n": 3}),
        (['names=["a", "b"]'], {"names": ["a", "b"]}),
        (["name=a"], {"name": "a"}),
        (["text=a=b"], {"text": "a=b"}),
    ],
)
def test_parse_options(options, expected):
    assert parse_options(options) == expected


def test_parse_options_without_value():
    with pytest.raises(ValueError, match="is not formatted as key=value"):
        parse_options(["foo"])


def test_main_with_file(tmp_wd, space_tool):
    """The figures, tables and metadata of a result file are written."""
    uri = str(space_tool.working_directory / "SpaceTool_result.hdf5")
    assert main(["--uri", uri, "--output-dir", "out", "--option", "n_samples=5"]) == 0
    directory = (
        tmp_wd / "out" / f"SpaceToolResult_{space_tool.result.metadata.tool_run_id}"
    )
    assert (directory / "figures" / "scatter_matrix.png").is_file()
    assert (directory / "tables" / "parameter_space.csv").is_file()
    assert (directory / "tables" / "settings.csv").is_file()
    metadata = json.loads((directory / "metadata.json").read_text())
    assert metadata["tool_run_id"] == space_tool.result.metadata.tool_run_id


def test_main_with_tool_run_id(tmp_wd, space_tool):
    """A result is loaded from its tool run id in an archive."""
    run_id = space_tool.result.metadata.tool_run_id
    assert (
        main([
            "--uri",
            f"tool-run:{run_id}",
            "--archive-root",
            "archive",
            "--output-dir",
            "out",
            "--no-figures",
        ])
        == 0
    )
    directory = tmp_wd / "out" / f"SpaceToolResult_{run_id}"
    assert not (directory / "figures").exists()
    assert (directory / "tables" / "parameter_space.csv").is_file()


def test_main_with_invalid_option(tmp_wd, space_tool, capsys):
    uri = str(space_tool.working_directory / "SpaceTool_result.hdf5")
    assert main(["--uri", uri, "--option", "foo=1"]) == 2
    assert "Invalid settings of the visualization" in capsys.readouterr().err


def test_main_list_options(tmp_wd, space_tool, capsys):
    uri = str(space_tool.working_directory / "SpaceTool_result.hdf5")
    assert main(["--uri", uri, "--list-options"]) == 0
    assert '"n_samples"' in capsys.readouterr().out
    assert not (tmp_wd / "visualization").exists()
