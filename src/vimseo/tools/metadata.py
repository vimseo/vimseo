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

    tool_run_id: str = ""
    """The unique identifier of the tool run which produced the result.

    The simulations executed by this run have it as their ``tool_run_id`` metadata,
    except those retrieved from the model cache (see
    :attr:`.simulation_run_ids`)."""

    parent_tool_run_id: str = ""
    """The identifier of the run of the tool which executed this tool, if any."""

    child_tool_run_ids: tuple[str, ...] = ()
    """The identifiers of the runs of the tools executed by this tool."""

    simulation_run_ids: tuple[str, ...] = ()
    """The ``run_id`` of the simulations used by the tool run, and by the tools it
    executed, in order of first use.

    It includes the simulations retrieved from the model cache, which were created
    by another run, and so it is the reference to find the simulations of a tool
    result. A tuple is used rather than a list because it is much faster to write
    to HDF5 when it has thousands of items."""
