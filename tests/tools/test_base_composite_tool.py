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

from pathlib import Path

import pytest
from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.tools.mock.mock_tool import MyBaseCompositeTool
from vimseo.tools.mock.mock_tool import MyTool


def test_composite_tool_settings_and_inputs_grammars(tmp_wd):
    """Check that Inputs and Settings grammars are correctly taken into account for a
    composite tool."""
    tool = MyBaseCompositeTool(subtools=[MyTool()])
    assert tool.option_names == ["foo", "composite_foo"]
    assert tool.settings_names == ["foo", "composite_foo"]
    options = {"composite_foo": "composite_", "foo": "_"}
    tool.execute(**options)
    assert tool.options == options
    assert tool.result.metadata.settings == {"composite_foo": "composite_", "foo": "_"}
    assert tool._subtools["MyTool"].result.metadata.settings == {"foo": "_"}


@pytest.mark.parametrize(
    "tool",
    [MyTool(), MyTool(working_directory="foo"), MyTool(root_directory="bar")],
)
@pytest.mark.parametrize(
    ("working_directory_after_construction", "directory_naming_method"),
    [
        ("", None),
        ("", DirectoryNamingMethod.NUMBERED),
        (Path("my_dir"), None),
    ],
)
def test_save_composite_tool_results(
    tmp_wd,
    working_directory_after_construction,
    directory_naming_method,
    tool,
):
    """Check that a :class:`.BaseCompositeTool` saves the result of each tool it is
    composed under the correct path."""
    if directory_naming_method:
        tool = MyBaseCompositeTool(
            subtools=[tool],
            directory_naming_method=directory_naming_method,
        )
    else:
        tool = MyBaseCompositeTool(subtools=[tool])
    if working_directory_after_construction != "":
        tool.working_directory = working_directory_after_construction

    expected_filename = "MyBaseCompositeTool"
    expected_subtool_filename = "MyTool"

    tool.execute()
    tool.save_results()

    if directory_naming_method == DirectoryNamingMethod.NUMBERED:
        assert tool.working_directory.name == "1"

    assert (tool.working_directory / f"{expected_filename}_result.hdf5").is_file()
    assert (
        tool.working_directory / "MyTool" / f"{expected_subtool_filename}_result.hdf5"
    ).is_file()
