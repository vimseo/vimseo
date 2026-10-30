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

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_result import BaseResult
from vimseo.analysis_nodes.base_settings import BaseInputs
from vimseo.analysis_nodes.doe.doe import DOEInputs
from vimseo.analysis_nodes.doe.doe import DOESettings
from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNode
from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNodeNoInputs
from vimseo.analysis_nodes.mock.mock_analysis_node import MyInputs
from vimseo.analysis_nodes.mock.mock_analysis_node import MySettings
from vimseo.analysis_nodes.result_visualization import BasePlotSettings


class PlottedResultSettings(BasePlotSettings):
    output_names: tuple[str, ...] = ()


@dataclass
class PlottedResult(BaseResult):
    """A result with a figure per output."""

    _PLOT_SETTINGS: ClassVar[type[PlottedResultSettings]] = PlottedResultSettings

    def _create_figures(self, settings):
        return {
            f"figure_{name}": Figure() for name in settings.output_names or ("a", "b")
        }


class InputsOnlyAnalysisNode(BaseAnalysisNode):
    """An analysis node exposing inputs but no settings."""

    _INPUTS = MyInputs

    @BaseAnalysisNode._validate
    def execute(self, inputs: MyInputs | None = None, **options):
        """A mock run."""


class ResultInputs(BaseInputs):
    result: BaseResult | None = None


class ResultInputAnalysisNode(BaseAnalysisNode):
    """An analysis node whose input is the result of another analysis node."""

    _INPUTS = ResultInputs

    _SETTINGS = MySettings

    @BaseAnalysisNode._validate
    def execute(self, inputs=None, settings=None, **options):
        """A mock run."""


class NoGrammarAnalysisNode(BaseAnalysisNode):
    """An analysis node without inputs nor settings (no option grammar)."""

    @BaseAnalysisNode._validate
    def execute(self, **options):
        """A mock run."""


class MissingSchemaJsonAnalysisNode(BaseAnalysisNode):
    """A JSON-grammar analysis node whose schema file does not exist."""

    _IS_JSON_GRAMMAR = True

    def execute(self, **options):
        """A mock run."""


def test_settings_and_inputs_as_kwargs(tmp_wd):
    """Check that Inputs and Settings grammars can be passed by keyword arguments and are
    correctly taken into account."""
    analysis_node = MyAnalysisNode()
    assert analysis_node._option_names == ["foo", "bar"]
    assert analysis_node._settings_names == ["foo"]
    options = {"foo": "_", "bar": "_"}
    analysis_node.execute(**options)
    assert analysis_node.options == options
    assert analysis_node.result.metadata.settings == {"foo": "_"}


def test_settings_and_inputs_as_pydantic(tmp_wd):
    """Check that Inputs and Settings grammars can be passed as Pydantic model instances
    and are correctly taken into account."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute(inputs=MyInputs(bar="_"), settings=MySettings(foo="_"))
    assert analysis_node.options == {"foo": "_", "bar": "_"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Either pass settings and inputs as a single `` **kwargs``, "
            "or use both ``inputs`` and ``settings`` args."
        ),
    ):
        analysis_node.execute(settings=MySettings(foo="_"), bar="_")

    analysis_node = MyAnalysisNodeNoInputs()
    analysis_node.execute(settings=MySettings(foo="_"))
    assert analysis_node.options == {"foo": "_"}


def test_inputs_only_analysis_node_grammar_and_names():
    """An inputs-only analysis node builds its grammar from the inputs model."""
    analysis_node = InputsOnlyAnalysisNode()
    assert analysis_node._option_names == ["bar"]
    assert analysis_node.input_names == ["bar"]
    # No settings model: settings_names and st_settings are empty/None.
    assert analysis_node._settings_names == []
    assert analysis_node._st_settings is None


def test_no_grammar_analysis_node_has_empty_options(tmp_wd):
    """An analysis node without inputs nor settings has no options."""
    analysis_node = NoGrammarAnalysisNode()
    analysis_node.execute()
    assert analysis_node.options == {}


def test_settings_and_st_settings_names():
    """The settings-related accessors expose the settings field names."""
    analysis_node = MyAnalysisNode()
    assert analysis_node.st_settings_names == ["foo"]


def test_settings_property_filters_options(tmp_wd):
    """The ``settings`` property only keeps the settings fields."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute(foo="x", bar="y")
    assert analysis_node._settings == {"foo": "x"}


def test_execute_with_inputs_only(tmp_wd):
    """Inputs can be passed alone, settings fall back to their defaults."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute(inputs=MyInputs(bar="x"))
    assert analysis_node.options["bar"] == "x"
    assert analysis_node.options["foo"] == ""


def test_execute_with_inputs_only_then_kwargs(tmp_wd):
    """Check that an analysis node executed with inputs only can then be executed with keyword
    arguments."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute(inputs=MyInputs(bar="x"))
    assert "inputs" not in analysis_node.options
    analysis_node.execute(foo="y")
    assert analysis_node.options == {"foo": "y", "bar": "x"}


@pytest.mark.parametrize(
    "get_options",
    [
        lambda result: {"result": result, "foo": "x"},
        lambda result: {
            "inputs": ResultInputs(result=result),
            "settings": MySettings(foo="x"),
        },
        lambda result: {"inputs": ResultInputs(result=result)},
    ],
)
def test_result_as_input(tmp_wd, get_options):
    """Check that an input that is the result of another analysis node is kept as is.

    Dumping a Pydantic model converts a dataclass into a dictionary.
    """
    result = BaseResult()
    analysis_node = ResultInputAnalysisNode()
    analysis_node.execute(**get_options(result))
    assert analysis_node.options["result"] is result


def test_missing_json_schema_raises():
    """Instantiating a JSON-grammar analysis node without its schema file raises."""
    with pytest.raises(ValueError, match="json schema does not exist"):
        MissingSchemaJsonAnalysisNode()


def test_check_options_wraps_invalid_data_error():
    """``_check_options`` re-raises grammar validation errors as InvalidDataError."""

    class FailingGrammar:
        def validate(self, options):
            msg = "invalid"
            raise InvalidDataError(msg)

    analysis_node = MyAnalysisNode()
    analysis_node._opt_grammar = FailingGrammar()
    with pytest.raises(
        InvalidDataError, match="Invalid options for analysis node MyAnalysisNode"
    ):
        analysis_node._check_options(foo="x")


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
    """Check that an analysis node saves its result under the correct path."""
    if directory_naming_method:
        analysis_node = MyAnalysisNode(
            directory_naming_method=directory_naming_method,
            working_directory=working_directory_in_constructor,
        )
    else:
        analysis_node = MyAnalysisNode(
            working_directory=working_directory_in_constructor
        )
    if working_directory_after_construction != "":
        analysis_node.working_directory = working_directory_after_construction
    analysis_node.execute()
    analysis_node.save_results(prefix)

    # When working_directory is not specified, root_directory has the name of analysis node.
    if (
        working_directory_after_construction == ""
        and working_directory_in_constructor == ""
    ):
        assert Path(analysis_node.name).is_dir()

    expected_filename = "MyAnalysisNode"
    if prefix == "":
        assert (
            analysis_node.working_directory / f"{expected_filename}_result.hdf5"
        ).is_file()
    else:
        assert (
            analysis_node.working_directory
            / f"{prefix}_{expected_filename}_result.hdf5"
        ).is_file()


@pytest.mark.parametrize(
    ("file_format", "prefix", "expected"),
    [
        ("hdf5", "", "DOEAnalysisNode_result.hdf5"),
        ("hdf5", "batch_1", "batch_1_DOEAnalysisNode_result.hdf5"),
        ("json", "", "DOEAnalysisNode_result.json"),
    ],
)
def test_get_result_file_name(file_format, prefix, expected):
    assert (
        BaseAnalysisNode.get_result_file_name("DOEAnalysisNode", file_format, prefix)
        == expected
    )


def test_save_and_load_results_hdf5(tmp_wd):
    """A result can be saved and reloaded from disk in HDF5 format."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute(foo="x")
    analysis_node.save_results()
    loaded = BaseAnalysisNode.load_results(
        analysis_node.working_directory / "MyAnalysisNode_result.hdf5"
    )
    assert isinstance(loaded, type(analysis_node.result))
    assert loaded.metadata.settings == {"foo": "x"}


def test_pickle_format_is_not_supported(tmp_wd):
    """The results are no longer saved nor loaded in pickle format."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute()
    with pytest.raises(ValueError, match="File format should be in"):
        analysis_node.save_results(file_format="pickle")
    with pytest.raises(ValueError, match="Unknow file format"):
        BaseAnalysisNode.load_results(
            analysis_node.working_directory / "MyAnalysisNode_result.pickle"
        )


def test_save_results_invalid_format_raises(tmp_wd):
    """Saving with an unsupported file format raises."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute()
    with pytest.raises(ValueError, match="File format should be in"):
        analysis_node.save_results(file_format="xml")


def test_load_results_json_from_base_analysis_node_raises(tmp_path):
    """Loading a JSON result from the base class is not supported."""
    with pytest.raises(ValueError, match="requires to call"):
        BaseAnalysisNode.load_results(tmp_path / "result.json")


def test_load_results_unknown_format_raises(tmp_path):
    """Loading an unknown file format raises."""
    with pytest.raises(ValueError, match="Unknow file format"):
        BaseAnalysisNode.load_results(tmp_path / "result.txt")


def test_load_options_from_metadata(tmp_wd, tmp_path):
    """Options can be restored from a metadata file on disk."""
    analysis_node = MyAnalysisNode()
    analysis_node.execute(foo="x")
    analysis_node.result.save_metadata_to_disk(tmp_path)
    analysis_node._working_directory = tmp_path

    analysis_node.load_options_from_metadata()
    assert analysis_node._options["foo"] == "x"


def test_load_options_from_metadata_missing_key_raises(tmp_path):
    """A metadata file without the options key raises a KeyError."""
    bad_file = tmp_path / "bad_metadata.json"
    bad_file.write_text(json.dumps({"not_settings": {}}))

    analysis_node = MyAnalysisNode()
    with pytest.raises(KeyError, match="settings"):
        analysis_node.load_options_from_metadata(file_path=bad_file)


@pytest.mark.parametrize(
    ("inputs", "settings", "msg"),
    [
        (
            MyAnalysisNode._INPUTS(),
            DOESettings(),
            "Settings must be of type <class 'vimseo.analysis_nodes.mock.mock_analysis_node.MySettings'>.",
        ),
        (
            DOEInputs(),
            MyAnalysisNode._SETTINGS(),
            "Inputs must be of type <class 'vimseo.analysis_nodes.mock.mock_analysis_node.MyInputs'>.",
        ),
    ],
)
def test_pass_wrong_settings_type(tmp_wd, inputs, settings, msg):
    """Check that an error is raised if the pydantic model passed as settings is not of
    expected type."""
    analysis_node = MyAnalysisNode()
    with pytest.raises(TypeError, match=re.escape(msg)):
        analysis_node.execute(settings=settings, inputs=inputs)


def test_constructor_options():
    """Check that an analysis node constructed with unexpected options raises an error."""
    with pytest.raises(
        TypeError,
        match=re.escape(
            "BaseAnalysisNode.__init__() got an unexpected keyword argument 'foo'"
        ),
    ):
        MyAnalysisNode(foo=1)
