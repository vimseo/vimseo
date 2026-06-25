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

"""A metadata attached to a tool result."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from vimseo.core.model_description import ModelDescription
from vimseo.tools.base_metadata import BaseMetadata


@dataclass
class ToolResultMetadata(BaseMetadata):
    """A metadata attached to a tool result.

    The metadata is attached to a result (:class:`.BaseResult`)
    of a tool (:class:`.BaseTool`). It stores information allowing
    the result to be self-supporting, allowing it to be processed by other tools
    (workflow approach).
    """

    _OPTIONS_KEY = "settings"

    settings: dict[str, Any] = field(default_factory=dict)
    """The options of a tool."""

    report: dict[str, str] = field(default_factory=dict)
    """The report of the corresponding tool execution."""

    model: ModelDescription | None = None
    """A description of the model under analysis."""
