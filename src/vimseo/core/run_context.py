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

"""The run of a tool, seen from the simulations it launches.

A tool (:class:`~vimseo.tools.base_tool.BaseTool`) executes models, and a model
result must be traceable to the tool run that asked for it, and conversely.
Both sides carry a unique identifier:

- a simulation has a ``run_id``, generated when the model is really run, and a
  ``tool_run_id``, which is the one of the tool run during which it was executed,
- a tool result has a ``run_id``, and the ``simulation_run_ids`` of all the
  simulations it used.

The tool run is made known to the models through a context variable, so that no
model or tool has to pass it to the other. A simulation retrieved from the model
cache is not run again: it keeps the ``run_id`` and the ``tool_run_id`` of the
run which created it, but it is also recorded as used by the current tool run.

Warnings:
    A context variable is local to a thread, and is not passed to a child
    process. The simulations executed by a thread or a process pool started
    during a tool run are therefore not recorded in its context.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Mapping

RUN_ID_NAME = "run_id"
"""The name of the model output holding the identifier of a simulation."""


def new_run_id() -> str:
    """Return a new unique identifier."""
    return uuid.uuid4().hex


@dataclass
class ToolRunContext:
    """The run of a tool, while it is executed."""

    tool_run_id: str
    """The unique identifier of the tool run."""

    tool_name: str
    """The name of the tool."""

    parent: ToolRunContext | None = None
    """The run of the tool executing this tool, if any."""

    simulation_run_ids: dict[str, None] = field(default_factory=dict)
    """The ``run_id`` of the simulations used by the tool run, and by the tool runs it
    launched, in order of first use.

    A dictionary is used as an ordered set."""

    child_tool_run_ids: list[str] = field(default_factory=list)
    """The identifiers of the tool runs launched by this tool run."""


_CURRENT_TOOL_RUN: ContextVar[ToolRunContext | None] = ContextVar(
    "vimseo_current_tool_run", default=None
)


def current_tool_run() -> ToolRunContext | None:
    """Return the tool run being executed, or ``None`` outside of a tool run."""
    return _CURRENT_TOOL_RUN.get()


@contextmanager
def tool_run(tool_name: str) -> Generator[ToolRunContext, None, None]:
    """Execute a block as a tool run.

    The run is a child of the current tool run, if any. When it ends, it is
    recorded in its parent, to which its simulations are added.

    Args:
        tool_name: The name of the tool.
    """
    parent = _CURRENT_TOOL_RUN.get()
    context = ToolRunContext(new_run_id(), tool_name, parent)
    token = _CURRENT_TOOL_RUN.set(context)
    try:
        yield context
    finally:
        _CURRENT_TOOL_RUN.reset(token)
        if parent is not None:
            parent.child_tool_run_ids.append(context.tool_run_id)
            parent.simulation_run_ids.update(context.simulation_run_ids)


def record_simulation(run_id: str) -> None:
    """Record a simulation as used by the current tool run, if any.

    Args:
        run_id: The ``run_id`` of the simulation.
    """
    context = _CURRENT_TOOL_RUN.get()
    if context is not None and run_id != "":
        context.simulation_run_ids[run_id] = None


def record_simulation_from_outputs(output_data: Mapping) -> None:
    """Record the simulation which produced some model outputs.

    Nothing is recorded if the outputs hold no ``run_id``, which is the case when a
    GEMSEO formulation has restricted the outputs of the model, e.g. in a calibration.

    Args:
        output_data: The outputs of a model.
    """
    if _CURRENT_TOOL_RUN.get() is None:
        return
    run_id = output_data.get(RUN_ID_NAME)
    if run_id is not None:
        record_simulation(str(np.atleast_1d(run_id)[0]))
