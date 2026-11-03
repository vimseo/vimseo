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

import logging
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.core.discipline.discipline import Discipline
from numpy import atleast_1d

from vimseo.core.gemseo_discipline_wrapper import GemseoDisciplineWrapper
from vimseo.core.model_metadata import MetaDataNames

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from gemseo.core.grammars.base_grammar import BaseGrammar

    from vimseo.core.load_case import LoadCase
    from vimseo.material.material import Material

LOGGER = logging.getLogger(__name__)


class BaseComponent(GemseoDisciplineWrapper):
    """A base component.

    A ``IntegratedModel`` executes a chain of ``BaseComponent``.

    Every component may read the error code of the upstream components, and may
    return its own, both under the name ``MetaDataNames.error_code``. A component that
    does not return an error code passes the upstream one on, so that the error code
    of the model is the last one returned along the chain.
    """

    _job_directory: Path | str
    """The fully-qualified job directory path."""

    USE_JOB_DIRECTORY: ClassVar[bool] = False
    """Whether to create a job directory."""

    is_run_component: bool = False
    """Whether the component runs the external software of its model.

    It is set by the model building the chain of components, e.g. on the
    run-processor of a :class:`.PreRunPostModel`, and gives the :attr:`.run` of the
    model.
    """

    _PERSISTENT_FILE_NAMES: ClassVar[Sequence[str]] = []
    """List of files produced in the scratch directory, to be copied to the archive
    directory."""

    auto_detect_grammar_files = True
    default_cache_type = Discipline.CacheType.HDF5
    default_grammar_type = Discipline.GrammarType.JSON

    def __init_subclass__(cls, **kwargs):
        """Reject the components still declaring the removed ``_ERROR_CODE_NAME``.

        Raises:
            AttributeError: When the component declares ``_ERROR_CODE_NAME``.
        """
        super().__init_subclass__(**kwargs)
        if "_ERROR_CODE_NAME" in cls.__dict__:
            msg = (
                f"The class attribute _ERROR_CODE_NAME of {cls.__name__} has been "
                f"removed: every component reads and returns its error code as "
                f"'{MetaDataNames.error_code.value}', so that the model gets it. "
                f"Remove it, and use MetaDataNames.error_code instead."
            )
            raise AttributeError(msg)

    def __init__(
        self,
        load_case: LoadCase | None = None,
        material_grammar_file: Path | str = "",
        material: Material | None = None,
        check_subprocess: bool = False,
    ) -> None:
        super().__init__()
        # A component may read the upstream error code and return its own; without
        # them in its grammars, GEMSEO would drop them and the model would report the
        # default one.
        self._declare_error_code(self.input_grammar)
        self._declare_error_code(self.output_grammar)
        self._load_case = load_case
        self._job_directory = ""
        self._check_subprocess = check_subprocess

        # """Initialize input grammar and default values from the material.

        # In strict (non-dynamic) mode, the material grammar is hard-coded in a json file.
        # In dynamic mode, the material grammar is defined from the material, itself being
        # defined from the json material values file. So the material grammar is generated
        # from the user-defined material values.
        # """

        if material_grammar_file != "":
            # Dynamic mode
            # temp_dir = tempfile.TemporaryDirectory()
            # dir_path = Path(temp_dir.name)
            # material.to_legacy_json_schema(write=True, dir_path=dir_path)
            # self.input_grammar.update_from_file(
            #     dir_path / f"{material_grammar_file.name}_legacy_grammar.json"
            # )
            # Would be the best solution but error parsing the schema.
            # self.input_grammar.update_from_schema(
            #     material_grammar_file.to_legacy_json_schema()
            # )
            # temp_dir.cleanup()
            # Strict mode:
            self.input_grammar.update_from_file(material_grammar_file)

        if material is not None:
            self.default_input_data.update({
                name: atleast_1d(value)
                for name, value in material.get_values_as_dict().items()
            })

    @staticmethod
    def _declare_error_code(grammar: BaseGrammar) -> None:
        """Declare the error code in a grammar as an optional variable.

        Args:
            grammar: The grammar. If it already declares the error code (e.g. from a
                grammar file), it is left unchanged.
        """
        error_code_name = MetaDataNames.error_code.value
        if error_code_name not in grammar:
            grammar.update_from_data({error_code_name: atleast_1d(0)})
            grammar.required_names.discard(error_code_name)

    @staticmethod
    def _get_upstream_error_code(input_data) -> int:
        """Return the error code reported by the upstream components.

        Args:
            input_data: The input data of the component.

        Returns:
            The upstream error code, or 0 if no upstream component reported one.
        """
        error_code = input_data.get(MetaDataNames.error_code.value)
        if error_code is None:
            return 0
        return int(atleast_1d(error_code)[0])

    @property
    def job_directory(self):
        return self._job_directory

    @property
    def job_name(self):
        return f"job_{self._job_directory.name}"
