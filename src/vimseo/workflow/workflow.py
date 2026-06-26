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

"""Chaining GEMSEO wrapped tools to run a workflow of tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from docstring_inheritance import GoogleDocstringInheritanceMeta
from gemseo.core.grammars.required_names import RequiredNames
from gemseo.mda.mda_chain import MDAChain
from gemseo.utils.string_tools import MultiLineString

from vimseo.tools.io.reader_tools_factory import ReaderToolsFactory
from vimseo.workflow.workflow_step import WorkflowStep

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping


class Workflow(metaclass=GoogleDocstringInheritanceMeta):
    """A workflow of tools."""

    def __init__(self, steps: Iterable[WorkflowStep]):
        self.__steps = steps
        self._chain = MDAChain(steps)
        self._chain.input_grammar._required_names = RequiredNames(
            self._chain.input_grammar
        )

    def execute(self, input_data: Mapping[str, Any] | None = None):
        return self._chain.execute(input_data)

    @property
    def steps(self) -> Mapping[str, WorkflowStep]:
        """The workflow steps."""
        return {step.name: step for step in self.__steps}

    @classmethod
    def from_json_path(cls, file_path: Path | str) -> Workflow:
        with Path(file_path).open() as f:
            step_settings = json.load(f)
            return cls([
                WorkflowStep.from_serialized_settings(**settings)
                for settings in step_settings
            ])

    @classmethod
    def from_json_buffer(cls, buf) -> Workflow:
        step_settings = json.load(buf)
        return cls([
            WorkflowStep.from_serialized_settings(**settings)
            for settings in step_settings
        ])

    def to_json(self) -> str:
        return json.dumps(
            [step.serialized_settings for step in self.__steps],
            indent=4,
        )

    def __str__(self):
        msg = MultiLineString()
        for step in self.__steps:
            msg.add(json.dumps(step.serialized_settings, indent=True))
            msg.add("")
        return str(msg)

    def _set_input_file_dir_path(self, path: str | Path):
        """Set the setting ``directory_path`` of the reader tools to the passed value."""
        reader_tool_names = ReaderToolsFactory().class_names
        for step in self.__steps:
            if step._tool_name in reader_tool_names:
                step._tool_settings.directory_path = str(path)
