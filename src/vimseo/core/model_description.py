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

from dataclasses import dataclass
from dataclasses import field
from json import dumps

from gemseo.utils.string_tools import MultiLineString
from numpy import ndarray

from vimseo.core.load_case import LoadCase


class BaseDescription:
    """A dummy base class for ruff to ``runtime-evaluated-base-classes``."""


@dataclass
class ModelDescription(BaseDescription):
    """The description of a model."""

    name: str = ""
    """The model name."""

    summary: str = ""
    """A brief description of the model ."""

    load_case: LoadCase = None
    """The load case."""

    dataflow: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    """The model dataflow."""

    default_inputs: dict[str, ndarray] = field(default_factory=dict)
    """The model default inputs."""

    curves: list[tuple[str]] = ()

    verbose: bool = False

    def _get_multiline(self):
        """A multiline representation of the load case as a ```MultiLineString``."""
        from vimseo.core.base_integrated_model import IntegratedModel

        text = MultiLineString()
        text.add(f"Model {self.name}: {self.summary}")

        text.add("")
        text.add("Load case:")
        text.indent()
        for line in self.load_case._get_multiline().lines:
            text.add(line.str_format)
        text.dedent()

        text.add("")
        text.add("Default values:")
        text.indent()
        for group_name in IntegratedModel.InputGroupNames:
            text.add("")
            text.add(f"Default {group_name}:")
            text.add(
                dumps(
                    self.default_inputs[group_name],
                    sort_keys=True,
                )
            )
        text.dedent()
        for key in ["model_inputs", "model_outputs"]:
            text.add(f"{key}:")
            text.indent()
            text.add(dumps(self.dataflow[key], sort_keys=True, indent=4))
            text.dedent()

        if self.verbose:
            dataflow = self.dataflow.copy()
            del dataflow["model_inputs"]
            del dataflow["model_outputs"]
            text.add("")
            text.add("Dataflow:")
            text.indent()
            text.add(dumps(dataflow, sort_keys=True, indent=4))
            text.dedent()
            text.add("Curves:")
            text.indent()
            text.add(str(self.curves))
            text.dedent()

        return text

    def __str__(self):
        return str(self._get_multiline())
