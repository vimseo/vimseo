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

import re
from pathlib import Path

import pytest
from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.tools.doe.doe import DOEInputs
from vimseo.tools.doe.doe import DOESettings
from vimseo.tools.mock.mock_tool import MyBaseCompositeTool
from vimseo.tools.mock.mock_tool import MyInputs
from vimseo.tools.mock.mock_tool import MySettings
from vimseo.tools.mock.mock_tool import MyTool
from vimseo.tools.mock.mock_tool import MyToolNoInputs


def test_settings_and_inputs_as_kwargs(tmp_wd):
    """Check that Inputs and Settings grammars can be passed by keyword arguments and are
    correctly taken into account."""
    tool = MyTool()
    assert tool.option_names == ["foo", "bar"]
    assert tool.settings_names == ["foo"]
    options = {"foo": "_", "bar": "_"}
    tool.execute(**options)
    assert tool.options == options
    assert tool.result.metadata.settings == {"foo": "_"}


def test_settings_and_inputs_as_pydantic(tmp_wd):
    """Check that Inputs and Settings grammars can be passed as Pydantic model instances
    and are correctly taken into account."""
    tool = MyTool()
    tool.execute(inputs=MyInputs(bar="_"), settings=MySettings(foo="_"))
    assert tool.options == {"foo": "_", "bar": "_"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            "You define keyword argument ``settings``. "
            "If you want to define inputs, it must be done through the keyword argument "
            "``inputs``."
        ),
    ):
        tool.execute(settings=MySettings(foo="_"), bar="_")

    tool = MyToolNoInputs()
    tool.execute(settings=MySettings(foo="_"))
    assert tool.options == {"foo": "_"}


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
    (
        "prefix",
        "working_directory_in_constructor",
        "working_directory_after_construction",
        "directory_naming_method",
    ),
    [
        ("", "", "", None),
        ("", "", "", DirectoryNamingMethod.NUMBERED),
        ("", Path("my_dir"), "", None),
        ("", "", Path("my_dir"), None),
        ("foo", Path("my_dir"), "", None),
    ],
)
def test_save_results(
    tmp_wd,
    prefix,
    working_directory_in_constructor,
    working_directory_after_construction,
    directory_naming_method,
):
    """Check that a tool saves its result under the correct path."""
    if directory_naming_method:
        tool = MyTool(
            directory_naming_method=directory_naming_method,
            working_directory=working_directory_in_constructor,
        )
    else:
        tool = MyTool(working_directory=working_directory_in_constructor)
    if working_directory_after_construction != "":
        tool.working_directory = working_directory_after_construction
    tool.execute()
    tool.save_results(prefix)

    # When working_directory is not specified, root_directory has the name of tool.
    if (
        working_directory_after_construction == ""
        and working_directory_in_constructor == ""
    ):
        assert Path(tool.name).is_dir()

    expected_filename = "MyTool"
    if prefix == "":
        assert (tool.working_directory / f"{expected_filename}_result.hdf5").is_file()
    else:
        assert (
            tool.working_directory / f"{prefix}_{expected_filename}_result.hdf5"
        ).is_file()


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


@pytest.mark.parametrize(
    ("inputs", "settings", "msg"),
    [
        (
            MyTool._INPUTS(),
            DOESettings(),
            "Settings must be of type <class 'vimseo.tools.mock.mock_tool.MySettings'>.",
        ),
        (
            DOEInputs(),
            MyTool._SETTINGS(),
            "Inputs must be of type <class 'vimseo.tools.mock.mock_tool.MyInputs'>.",
        ),
    ],
)
def test_pass_wrong_settings_type(tmp_wd, inputs, settings, msg):
    """Check that an error is raised if the pydantic model passed as settings is not of
    expected type."""
    tool = MyTool()
    with pytest.raises(TypeError, match=re.escape(msg)):
        tool.execute(settings=settings, inputs=inputs)


def test_constructor_options():
    """Check that a tool constructed with unexpected options raises an error."""
    with pytest.raises(
        TypeError,
        match=re.escape("BaseTool.__init__() got an unexpected keyword argument 'foo'"),
    ):
        MyTool(foo=1)
