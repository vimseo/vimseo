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

import pytest
from gemseo.core.grammars.errors import InvalidDataError

from vimseo.tools.base_result import BaseResult
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.mock.mock_tool import MyInputs
from vimseo.tools.mock.mock_tool import MyTool


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


def test_set_plot_uses_plot_factory():
    """``set_plot`` delegates to the plot factory when one is set."""

    class DummyFactory:
        def create(self, class_name, **options):
            return ("plot", class_name, options)

    tool = MyTool()
    tool._plot_factory = DummyFactory()
    tool.set_plot("Scatter", color="red")
    assert tool._plot == ("plot", "Scatter", {"color": "red"})
    assert tool._plot_class == "Scatter"


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


def test_save_and_load_results_pickle(tmp_wd):
    """A pickled result can be saved and reloaded from disk."""
    tool = MyTool()
    tool.execute(foo="x")
    tool.save_results(file_format="pickle")
    path = tool.working_directory / "MyTool_result.pickle"
    assert path.is_file()

    loaded = BaseTool.load_results(path)
    assert isinstance(loaded, BaseResult)


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


def test_load_options_from_metadata(tmp_path):
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
