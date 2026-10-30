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

"""The run of an analysis node, seen from the simulations it launches.

An analysis node (:class:`~vimseo.analysis_nodes.base_analysis_node.BaseAnalysisNode`) executes models, and a model
result must be traceable to the analysis node run that asked for it, and conversely.
Both sides carry a unique identifier:

- a simulation has a ``run_id``, generated when the model is really run, and a
  ``analysis_node_run_id``, which is the one of the analysis node run during which it was executed,
- an analysis node result has a ``run_id``, and the ``simulation_run_ids`` of all the
  simulations it used.

The analysis node run is made known to the models through a context variable, so that no
model or analysis node has to pass it to the other. A simulation retrieved from the model
cache is not run again: it keeps the ``run_id`` and the ``analysis_node_run_id`` of the
run which created it, but it is also recorded as used by the current analysis node run.

Warnings:
    A context variable is local to a thread, and is not passed to a child
    process. The simulations executed by a thread or a process pool started
    during an analysis node run are therefore not recorded in its context.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Mapping

RUN_ID_NAME = "run_id"
"""The name of the model output holding the identifier of a simulation."""


def new_run_id() -> str:
    """Return a new unique identifier, sorted by its date of creation.

    It is the UTC date of creation, to the second, followed by the start of a random
    UUID, e.g. ``20261019T104610_e5c1a9d7``: sorting identifiers alphabetically sorts
    them chronologically, without any coordination between processes, and the UUID
    part makes them unique.
    """
    return f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}_{uuid.uuid4().hex[:8]}"


@dataclass
class AnalysisNodeRunContext:
    """The run of an analysis node, while it is executed."""

    analysis_node_run_id: str
    """The unique identifier of the analysis node run."""

    analysis_node_name: str
    """The name of the analysis node."""

    parent: AnalysisNodeRunContext | None = None
    """The run of the analysis node executing this analysis node, if any."""

    simulation_run_ids: dict[str, None] = field(default_factory=dict)
    """The ``run_id`` of the simulations used by the analysis node run, and by the analysis node runs it
    launched, in order of first use.

    A dictionary is used as an ordered set."""

    child_analysis_node_run_ids: list[str] = field(default_factory=list)
    """The identifiers of the analysis node runs launched by this analysis node run."""


_CURRENT_ANALYSIS_NODE_RUN: ContextVar[AnalysisNodeRunContext | None] = ContextVar(
    "vimseo_current_analysis_node_run", default=None
)


def current_analysis_node_run() -> AnalysisNodeRunContext | None:
    """Return the analysis node run being executed, or ``None`` outside of an analysis node run."""
    return _CURRENT_ANALYSIS_NODE_RUN.get()


@contextmanager
def analysis_node_run(
    analysis_node_name: str,
) -> Generator[AnalysisNodeRunContext, None, None]:
    """Execute a block as an analysis node run.

    The run is a child of the current analysis node run, if any. When it ends, it is
    recorded in its parent, to which its simulations are added.

    Args:
        analysis_node_name: The name of the analysis node.
    """
    parent = _CURRENT_ANALYSIS_NODE_RUN.get()
    context = AnalysisNodeRunContext(new_run_id(), analysis_node_name, parent)
    token = _CURRENT_ANALYSIS_NODE_RUN.set(context)
    try:
        yield context
    finally:
        _CURRENT_ANALYSIS_NODE_RUN.reset(token)
        if parent is not None:
            parent.child_analysis_node_run_ids.append(context.analysis_node_run_id)
            parent.simulation_run_ids.update(context.simulation_run_ids)


def record_simulation(run_id: str) -> None:
    """Record a simulation as used by the current analysis node run, if any.

    Args:
        run_id: The ``run_id`` of the simulation.
    """
    context = _CURRENT_ANALYSIS_NODE_RUN.get()
    if context is not None and run_id != "":
        context.simulation_run_ids[run_id] = None


def record_simulation_from_outputs(output_data: Mapping) -> None:
    """Record the simulation which produced some model outputs.

    Nothing is recorded if the outputs hold no ``run_id``, which is the case when a
    GEMSEO formulation has restricted the outputs of the model, e.g. in a calibration.

    Args:
        output_data: The outputs of a model.
    """
    if _CURRENT_ANALYSIS_NODE_RUN.get() is None:
        return
    run_id = output_data.get(RUN_ID_NAME)
    if run_id is not None:
        record_simulation(str(np.atleast_1d(run_id)[0]))
