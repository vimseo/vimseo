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

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pytest
from gemseo.core.grammars.errors import InvalidDataError
from gemseo.utils.directory_creator import DirectoryNamingMethod
from plotly.graph_objs import Figure

from vimseo.tools.base_result import BaseResult
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.doe.doe import DOEInputs
from vimseo.tools.doe.doe import DOESettings
from vimseo.tools.mock.mock_tool import MyInputs
from vimseo.tools.mock.mock_tool import MySettings
from vimseo.tools.mock.mock_tool import MyTool
from vimseo.tools.mock.mock_tool import MyToolNoInputs
from vimseo.tools.result_visualization import BaseVisualizationSettings


class PlottedResultSettings(BaseVisualizationSettings):
    output_names: tuple[str, ...] = ()


@dataclass
class PlottedResult(BaseResult):
    """A result with a figure per output."""

    _VISUALIZATION_SETTINGS: ClassVar[type[PlottedResultSettings]] = (
        PlottedResultSettings
    )

    def _create_figures(self, settings):
        return {
            f"figure_{name}": Figure() for name in settings.output_names or ("a", "b")
        }


class InputsOnlyTool(BaseTool):
    """A tool exposing inputs but no settings."""

    _INPUTS = MyInputs

    @BaseTool.validate
    def execute(self, inputs: MyInputs | None = None, **options):
        """A mock run."""


class NoGrammarTool(BaseTool):
    """A tool without inputs nor settings (no option grammar)."""

    @BaseTool.validate
    def execute(self, **options):
        """A mock run."""


class MissingSchemaJsonTool(BaseTool):
    """A JSON-grammar tool whose schema file does not exist."""

    _IS_JSON_GRAMMAR = True

    def execute(self, **options):
        """A mock run."""


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
            "Either pass settings and inputs as a single `` **kwargs``, "
            "or use both ``inputs`` and ``settings`` args."
        ),
    ):
        tool.execute(settings=MySettings(foo="_"), bar="_")

    tool = MyToolNoInputs()
    tool.execute(settings=MySettings(foo="_"))
    assert tool.options == {"foo": "_"}


def test_inputs_only_tool_grammar_and_names():
    """An inputs-only tool builds its grammar from the inputs model."""
    tool = InputsOnlyTool()
    assert tool.option_names == ["bar"]
    assert tool.input_names == ["bar"]
    # No settings model: settings_names and st_settings are empty/None.
    assert tool.settings_names == []
    assert tool._st_settings is None


def test_no_grammar_tool_has_empty_options(tmp_wd):
    """A tool without inputs nor settings has no options."""
    tool = NoGrammarTool()
    tool.execute()
    assert tool.options == {}


def test_settings_and_st_settings_names():
    """The settings-related accessors expose the settings field names."""
    tool = MyTool()
    assert tool.st_settings_names == ["foo"]


def test_settings_property_filters_options(tmp_wd):
    """The ``settings`` property only keeps the settings fields."""
    tool = MyTool()
    tool.execute(foo="x", bar="y")
    assert tool.settings == {"foo": "x"}


def test_execute_with_inputs_only(tmp_wd):
    """Inputs can be passed alone, settings fall back to their defaults."""
    tool = MyTool()
    tool.execute(inputs=MyInputs(bar="x"))
    assert tool.options["bar"] == "x"
    assert tool.options["foo"] == ""


def test_missing_json_schema_raises():
    """Instantiating a JSON-grammar tool without its schema file raises."""
    with pytest.raises(ValueError, match="json schema does not exist"):
        MissingSchemaJsonTool()


def test_check_options_wraps_invalid_data_error():
    """``_check_options`` re-raises grammar validation errors as InvalidDataError."""

    class FailingGrammar:
        def validate(self, options):
            msg = "invalid"
            raise InvalidDataError(msg)

    tool = MyTool()
    tool._opt_grammar = FailingGrammar()
    with pytest.raises(InvalidDataError, match="Invalid options for tool MyTool"):
        tool._check_options(foo="x")


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
    ("file_format", "prefix", "expected"),
    [
        ("hdf5", "", "DOETool_result.hdf5"),
        ("hdf5", "batch_1", "batch_1_DOETool_result.hdf5"),
        ("json", "", "DOETool_result.json"),
    ],
)
def test_get_result_file_name(file_format, prefix, expected):
    assert BaseTool.get_result_file_name("DOETool", file_format, prefix) == expected


def test_save_and_load_results_hdf5(tmp_wd):
    """A result can be saved and reloaded from disk in HDF5 format."""
    tool = MyTool()
    tool.execute(foo="x")
    tool.save_results()
    loaded = BaseTool.load_results(tool.working_directory / "MyTool_result.hdf5")
    assert isinstance(loaded, type(tool.result))
    assert loaded.metadata.settings == {"foo": "x"}


def test_pickle_format_is_not_supported(tmp_wd):
    """The results are no longer saved nor loaded in pickle format."""
    tool = MyTool()
    tool.execute()
    with pytest.raises(ValueError, match="File format should be in"):
        tool.save_results(file_format="pickle")
    with pytest.raises(ValueError, match="Unknow file format"):
        BaseTool.load_results(tool.working_directory / "MyTool_result.pickle")


def test_plot_results_is_deprecated(tmp_wd):
    """The deprecated plot_results visualizes the result of the tool in its working
    directory, converting the former option selecting a single variable."""
    tool = MyTool()
    tool.execute()
    tool.result = PlottedResult()
    with pytest.warns(DeprecationWarning, match=r"BaseResult\.visualize"):
        figures = tool.plot_results(save=True, show=False, output_name="b")
    assert list(figures) == ["figure_b"]
    assert (tool.working_directory / "figure_b.html").is_file()


def test_save_results_invalid_format_raises(tmp_wd):
    """Saving with an unsupported file format raises."""
    tool = MyTool()
    tool.execute()
    with pytest.raises(ValueError, match="File format should be in"):
        tool.save_results(file_format="xml")


def test_load_results_json_from_base_tool_raises(tmp_path):
    """Loading a JSON result from the base class is not supported."""
    with pytest.raises(ValueError, match="requires to call"):
        BaseTool.load_results(tmp_path / "result.json")


def test_load_results_unknown_format_raises(tmp_path):
    """Loading an unknown file format raises."""
    with pytest.raises(ValueError, match="Unknow file format"):
        BaseTool.load_results(tmp_path / "result.txt")


def test_load_options_from_metadata(tmp_wd, tmp_path):
    """Options can be restored from a metadata file on disk."""
    tool = MyTool()
    tool.execute(foo="x")
    tool.result.save_metadata_to_disk(tmp_path)
    tool._working_directory = tmp_path

    tool.load_options_from_metadata()
    assert tool._options["foo"] == "x"


def test_load_options_from_metadata_missing_key_raises(tmp_path):
    """A metadata file without the options key raises a KeyError."""
    bad_file = tmp_path / "bad_metadata.json"
    bad_file.write_text(json.dumps({"not_settings": {}}))

    tool = MyTool()
    with pytest.raises(KeyError, match="settings"):
        tool.load_options_from_metadata(file_path=bad_file)


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
