# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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

import datetime
import functools
import inspect
import json
import logging
import pickle
from abc import abstractmethod
from copy import deepcopy
from os.path import join
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from docstring_inheritance import GoogleDocstringInheritanceMeta
from gemseo.core.grammars.errors import InvalidDataError
from gemseo.core.grammars.json_grammar import JSONGrammar
from gemseo.utils.directory_creator import DirectoryCreator
from gemseo.utils.directory_creator import DirectoryNamingMethod
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.io.io_factory import IOFactory
from vimseo.tools.base_result import BaseResult
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.metadata import ToolResultMetadata
from vimseo.tools.tool_results_factory import ToolResultsFactory

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence

    from plotly.graph_objects import Figure
    from pydantic import BaseModel

    from vimseo.tools.base_settings import BaseInputs

LOGGER = logging.getLogger(__name__)


class ToolConstructorSettings(BaseSettings):
    name: str = Field(
        default="",
        description="The name of the tool. By default, it is the class name.",
    )
    root_directory: str | Path = Field(
        default=config.root_directory,
        description="The path to the root directory, wherein unique directories will be created at each execution. If set to empty string, use the current working directory.",
    )
    directory_naming_method: DirectoryNamingMethod = Field(
        default=DirectoryNamingMethod.NUMBERED,
        description="The method to create the execution directories.",
    )
    working_directory: str | Path = Field(
        default=config.working_directory,
        description="The directory within which to save the results. "
        "If empty, save the results into the unique generated directory. "
        "Note that the use of a user-defined working_directory or an automatically generated unique directory is exclusive, "
        "and the choice is controlled by using leaving or not working_directory to its default value.",
    )


class StreamlitToolConstructorSettings(ToolConstructorSettings):
    root_directory: str = config.root_directory
    directory_naming_method: str = DirectoryNamingMethod.UUID
    working_directory: str = config.working_directory


class BaseTool(metaclass=GoogleDocstringInheritanceMeta):
    """A base tool to be inherited to implement specific purpose tools.

    The tool options can be checked versus a grammar.
    Option checking is enable through :attr:`_HAS_OPTION_CHECK`.
    Settings can be passed at construction or through :meth:`~.execute`.
    The tool result can be written on disk, and then loaded.
    In the example below, ``Tool`` should be replaced by an available tool.

    Examples:
        >>> from vimseo.tools.example_tool import MyTool
        >>> tool = MyTool()
        >>> tool.execute()
        >>> print(tool.result)
        # The result can be saved on disk.
        >>> tool.save_results()
        # Optionnaly, the current options of the tool can be saved on disk.
        >>> tool.result.save_metadata_to_disk()
        # The result saved on disk can be loaded.
        >>> results = BaseTool.load_results(tool.working_directory /
        >>> 'Tool_result.pickle')
        # Then, the tool can plot the result. Note that the :meth:`plot_results` method
        # takes the result as input. In the future, this method will be moved from the
        # tools to a post processor class.
        >>> tool.plot_results(results, save=True, show=False)
    """

    results: BaseResult | None
    """The results of the tool."""

    _root_directory: Path
    """The directory where execution results are written."""

    _opt_grammar: JSONGrammar | BaseModel
    """The json schema used to validate  the :attr:`_options`."""

    _options: dict
    """The current options used to execute the tool."""

    _plot_factory: str | None
    """The plot factory used to generate the plot instance."""

    _IS_JSON_GRAMMAR = False

    _INPUTS: ClassVar[BaseInputs | None] = None
    """The model describing the inputs."""

    _SETTINGS: ClassVar[BaseSettings | None] = None
    """The model describing the settings."""

    _STREAMLIT_SETTINGS: ClassVar[BaseSettings | None] = None
    """The model describing the settings for interfacing with Streamlit."""

    _HAS_OPTION_CHECK: ClassVar[bool] = True
    """Whether the tool uses option checking."""

    _RESULT_SUFFIX: ClassVar[str] = "_result"

    _RESULT_FORMATS: ClassVar[Sequence[str]] = ["hdf5", "json", "pickle"]

    _STREAMLIT_CONSTRUCTOR_OPTIONS = StreamlitToolConstructorSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        name: str = "",
    ):
        """
        # TODO allow passing pydantic model
        Args:
            root_directory: The path to the root directory,
                wherein unique directories will be created at each execution.
                If set to empty string, use the current working directory.
            directory_naming_method: The method to create the execution directories.
            working_directory: The directory within which to save the results.
                If empty, save the results into the unique generated directory.
                Note that the use of a user-defined working_directory or an
                automatically generated unique directory is exclusive, and the choice
                is controlled by using leaving or not working_directory to its default
                value.
            name: The name of the tool. By default, it is the class name.
        """
        options = ToolConstructorSettings(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            name=name,
        ).model_dump()
        self.name = (
            self.__class__.__name__ if options["name"] == "" else options["name"]
        )
        options = ToolConstructorSettings(**options).model_dump()
        self.time = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        self.result = BaseResult()
        self.report_name = f"{self.__class__.__name__} Report"
        root_directory = (
            Path(self.name)
            if options["root_directory"] == ""
            else options["root_directory"]
        )
        self._working_directory = options["working_directory"]

        self._directory_creator = DirectoryCreator(
            root_directory=root_directory,
            directory_naming_method=options["directory_naming_method"],
        )

        self._has_check_options = self._HAS_OPTION_CHECK
        self._opt_grammar = None
        self._plot_factory = None

        if self._IS_JSON_GRAMMAR:
            f_class = inspect.getfile(self.__class__)
            self._load_grammar(self.__class__.__name__, f_class)
            self._options = {}
        else:
            if self._SETTINGS is not None:
                if self._INPUTS is None:
                    self._opt_grammar = deepcopy(self._SETTINGS)
                else:

                    class Settings(self._INPUTS, self._SETTINGS):
                        """The options of the tool."""

                    self._opt_grammar = deepcopy(Settings)
            elif self._INPUTS is not None:
                self._opt_grammar = deepcopy(self._INPUTS)

            self._options = (
                self._opt_grammar().model_dump()
                if self._opt_grammar is not None
                else {}
            )

        if self._SETTINGS is not None:
            self._st_settings = (
                deepcopy(self._SETTINGS)
                if self._STREAMLIT_SETTINGS is None
                else deepcopy(self._STREAMLIT_SETTINGS)
            )
        else:
            self._st_settings = None

    @property
    def working_directory(self) -> Path:
        return self._directory_creator.last_directory or Path(self._working_directory)

    @working_directory.setter
    def working_directory(self, value: str | Path) -> None:
        self._working_directory = value

    @property
    def option_names(self):
        """The names of the options that can be passed to ``execute()``."""
        if isinstance(self._opt_grammar, JSONGrammar):
            return self._opt_grammar.names
        return list(self._opt_grammar.model_fields.keys())

    def get_filtered_options(self, **options):
        return {
            name: option
            for name, option in options.items()
            if name in self.option_names
        }

    def _create_working_directory(self) -> None:
        """Create the working directory using either a user-defined name or an
        automatically generated unique name."""
        if self._working_directory == "":
            self._directory_creator.create()
        else:
            Path(self._working_directory).mkdir(exist_ok=True, parents=True)
        LOGGER.info(
            f"Working directory is {self.working_directory.absolute().resolve()}"
        )

    def set_plot(self, class_name, **options) -> None:
        """Set the type of plot to show the results of this tool.

        Args:
            class_name: The name of the plot class.
            **options: The options of the plot constructor.
        """
        if self._plot_factory:
            self._plot = self._plot_factory.create(class_name, **options)
        self._plot_class = class_name

    def update_options(self, **options):
        self._options.update(options)

    def _load_grammar(self, cls_name: str, f_class: str) -> None:
        """Load the grammar used to validate the options.

        Args:
            cls_name: The class name.
            f_class: The file containing the class.
        """
        self._opt_grammar = JSONGrammar("Tool")
        name = cls_name + "_options"
        if self._has_check_options:
            comp_dir = Path(Path(f_class).parent).resolve()
            schema_file = join(comp_dir, f"{name}.json")  # noqa: PTH118
            if not Path(schema_file).exists():
                msg = (
                    "Settings grammar for {} tool json schema does not exist, "
                    "expected: {}".format(cls_name, join(comp_dir, name + ".json"))  # noqa: PTH118
                )
                raise ValueError(msg)
            self._opt_grammar.update_from_file(schema_file)

    @property
    def options(self):
        """The options of the tool."""
        return self._options

    @property
    def grammar(self):
        """The validation grammar."""
        return self._opt_grammar

    @property
    def settings_names(self) -> Iterable[str]:
        if self._SETTINGS is not None:
            return list(self._SETTINGS.model_fields.keys())
        return []

    @property
    def input_names(self) -> Iterable[str]:
        if self._INPUTS is not None:
            return list(self._INPUTS.model_fields.keys())
        return []

    @property
    def settings(self):
        return {
            name: value
            for name, value in self.options.items()
            if name in self.settings_names
        }

    @property
    def st_settings_names(self) -> Iterable[str]:
        return list(self._st_settings.model_fields.keys())

    def _pre_process_options(self, **options):
        self.update_options(**options)

        if not self._HAS_OPTION_CHECK:
            return options

        if isinstance(self._opt_grammar, JSONGrammar):
            self._check_options(**self._options)
        elif self._opt_grammar is None:
            self._options = {}
        else:
            if "settings" in options:
                if self._INPUTS is not None and not set(options.keys()).issubset({
                    "settings",
                    "inputs",
                }):
                    msg = (
                        "You define keyword argument ``settings``. "
                        "If you want to define inputs, it must be done through "
                        "the keyword argument ``inputs``."
                    )
                    raise ValueError(msg)
                if not isinstance(options["settings"], self._SETTINGS):
                    msg = f"Settings must be of type {self._SETTINGS}."
                    raise TypeError(msg)
                self._options = options["settings"].model_dump()
                if self._INPUTS is not None:
                    self._options.update(self._INPUTS().model_dump())
                if "inputs" in options:
                    if not isinstance(options["inputs"], self._INPUTS):
                        msg = f"Inputs must be of type {self._INPUTS}."
                        raise TypeError(msg)
                    self._options.update(options["inputs"].model_dump())
            elif "inputs" in options:
                self._options.update(options["inputs"].model_dump())
                if self._SETTINGS is not None:
                    self._options.update(self._SETTINGS().model_dump())
            else:
                self._options = self._opt_grammar(**self._options).model_dump()

        return self._options

    def validate(f):  # noqa: N805
        @functools.wraps(f)
        def decorated(self, *args, **options):
            self._create_working_directory()
            options = self._pre_process_options(**options)
            f(self, *args, **options)
            self._set_options_to_results(options)
            return self.result

        return decorated

    @abstractmethod
    def execute(self, *args, **options):
        """The user-defined treatment called by :meth:`execute`.

        Args:
            options: The options of the execution.
        """

    @classmethod
    def load_results(cls, path: Path):
        """Load a result of a tool from the disk.

        For a `JSON` file, only `SpaceToolResult` is supported.
        This method must be called from class `SpaceTool`.
        `JSON` format for tool results is deprecated.

        Args:
            path: The path to the file.
            tool_name: The name of the tool associated with the result under stored
            in ``path``.
        """
        import h5py

        path = Path(path)
        if path.suffix == ".hdf5":
            class_name = ""
            with h5py.File(path, "r") as f:
                class_name = f.attrs["__class__"]
            tmp_result = ToolResultsFactory().create(class_name)
            return type(tmp_result).from_hdf5(path)
        # TODO remove support for json
        if path.suffix == ".json":
            if cls.__name__ == "BaseTool":
                msg = (
                    "Loading tool result from JSON format requires to call "
                    "load_results from the tool class associated with the result stored "
                    "in the JSON file."
                )
                raise ValueError(msg)
            LOGGER.warning("Loading tool results from JSON format is deprecated.")
            io = IOFactory().create(f"{cls.__name__}FileIO")
            return io.read(
                file_name=path,
            )
        if path.suffix == ".pickle":
            with Path(path).open("rb") as f:
                return pickle.load(f)

        msg = f"Unknow file format {path.suffix}. Supported formats are {cls._RESULT_FORMATS}"
        raise ValueError(msg)

    def _set_options_to_results(self, options):
        """Set current tool options to the metadata field of the results."""
        self.result.metadata.settings = {
            name: value
            for name, value in options.items()
            if name in self.settings_names
        }

    def load_options_from_metadata(self, file_path: str | Path | None = None):
        """Load a result of a tool from the disk.

        Args:
            file_path: The path to the file.
        """
        file_path = (
            self._working_directory / f"{self.result.__class__.__name__}_metadata.json"
            if file_path is None
            else file_path
        )
        with Path(file_path).open() as f:
            loaded_metadata = json.load(f)
            if ToolResultMetadata._OPTIONS_KEY not in loaded_metadata:
                msg = f"Loaded options must contain the key '{ToolResultMetadata._OPTIONS_KEY}'"
                raise KeyError(msg)
            loaded_options = loaded_metadata[ToolResultMetadata._OPTIONS_KEY]
            if self._has_check_options:
                self._check_options(**loaded_options)
            self._options.update(loaded_options)

    def save_results(self, prefix: str = "", file_format="hdf5") -> None:
        """Save the results of the tool on disk. The file path is
       `BaseTool.working_directory` / ``{filename}_result.{file_format}``.

        Args:
            prefix: The prefix of the filename result.
        """
        prefix_separator = ""
        if prefix != "":
            prefix_separator = "_"

        path = (
            self.working_directory
            / f"{prefix}{prefix_separator}{self.name}{self._RESULT_SUFFIX}.{file_format}"
        )
        LOGGER.info(f"Saving result to {path.absolute().resolve()}")

        if file_format not in self._RESULT_FORMATS:
            msg = f"File format should be in {self._RESULT_FORMATS}"
            raise ValueError(msg)

        if file_format == "hdf5":
            self.result.to_hdf5(path)
        elif file_format == "json":
            io = IOFactory().create(f"{self.name}FileIO")
            io.write(self.result, directory_path=path.parent, file_base_name=path.stem)
        elif file_format == "pickle":
            self.result.to_pickle(path)

    # TODO Choose if it is a class method or not
    @abstractmethod
    def plot_results(
        self,
        result: BaseResult,
        directory_path: str | Path = "",
        save=False,
        show=True,
        **options,
    ) -> Mapping[str, Figure]:
        """Plot criteria for a given variable name.

        Args:
            result: The result of the tool.
            directory_path: The path under which the plots are saved.
            save: Whether to save the plot on disk.
            show: Whether to show the plot.
            options: The options of the plot.
        """

    def _check_options(self, **options) -> None:
        """Check the options of the passed at execution of the tool. It is not
        automatically called. Typically, it can be called in :meth:`~.execute` before
        using the options.

        Args:
            **options: The options of the post-processor.

        Raises:
            InvalidDataError: If an option is invalid according to the grammar.
        """
        if self._opt_grammar is not None:
            try:
                self._opt_grammar.validate(options)
            except InvalidDataError as err:
                msg = f"Invalid options for tool {self.name}; got: {options}"
                raise InvalidDataError(msg) from err
