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

"""A metadata attached to an analysis node result."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from vimseo.analysis_nodes.base_metadata import BaseMetadata
from vimseo.core.model_description import ModelDescription


@dataclass
class AnalysisNodeResultMetadata(BaseMetadata):
    """A metadata attached to an analysis node result.

    The metadata is attached to a result (:class:`.BaseResult`)
    of an analysis node (:class:`.BaseAnalysisNode`). It stores information allowing
    the result to be self-supporting, allowing it to be processed by other analysis nodes
    (workflow approach).
    """

    _OPTIONS_KEY = "settings"

    settings: dict[str, Any] = field(default_factory=dict)
    """The options of an analysis node."""

    report: dict[str, str] = field(default_factory=dict)
    """The report of the corresponding analysis node execution."""

    model: ModelDescription | None = None
    """A description of the model under analysis."""

    analysis_node_run_id: str = ""
    """The unique identifier of the analysis node run which produced the result.

    The simulations executed by this run have it as their ``analysis_node_run_id`` metadata,
    except those retrieved from the model cache (see
    :attr:`.simulation_run_ids`)."""

    parent_analysis_node_run_id: str = ""
    """The identifier of the run of the analysis node which executed this analysis node, if any."""

    child_analysis_node_run_ids: tuple[str, ...] = ()
    """The identifiers of the runs of the analysis nodes executed by this analysis node."""

    simulation_run_ids: tuple[str, ...] = ()
    """The ``run_id`` of the simulations used by the analysis node run, and by the analysis nodes it
    executed, in order of first use.

    It includes the simulations retrieved from the model cache, which were created
    by another run, and so it is the reference to find the simulations of an analysis node
    result. A tuple is used rather than a list because it is much faster to write
    to HDF5 when it has thousands of items."""
