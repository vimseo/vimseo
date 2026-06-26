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

from numpy import atleast_1d

from vimseo.core.gemseo_discipline_wrapper import GemseoDisciplineWrapper

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from vimseo.material.material import Material

LOGGER = logging.getLogger(__name__)


class BaseComponent(GemseoDisciplineWrapper):
    """A base component.

    A ``IntegratedModel`` executes a chain of ``BaseComponent``.
    """

    _job_directory: Path | str
    """The fully-qualified job directory path."""

    USE_JOB_DIRECTORY: ClassVar[bool] = False
    """Whether to create a job directory."""

    _PERSISTENT_FILE_NAMES: ClassVar[Sequence[str]] = []
    """List of files produced in the scratch directory, to be copied to the archive
    directory."""

    def __init__(
        self,
        load_case_name: str,
        material_grammar_file: Path | str = "",
        material: Material | None = None,
    ) -> None:
        super().__init__()
        self._load_case_name = load_case_name
        self._job_directory = ""

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

    @property
    def job_directory(self):
        return self._job_directory

    @property
    def job_name(self):
        return f"job_{self._job_directory.name}"
