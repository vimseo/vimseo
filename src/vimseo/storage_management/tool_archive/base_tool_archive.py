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

"""The archive of the results of the tools."""

from __future__ import annotations

import json
from abc import abstractmethod
from dataclasses import fields
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from docstring_inheritance import GoogleDocstringInheritanceMeta

import vimseo
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.tools.base_result import BaseResult


def _to_json_value(value: Any) -> Any:
    """Convert a value that :mod:`json` cannot encode, without ever failing.

    The settings of a tool can hold any object, like a model. An OpenTURNS
    distribution, like the prior of a Bayesian analysis, is described in clear
    (see :func:`.ot_distribution_to_dict`), else by its short form.
    """
    from vimseo.utilities.ot_distribution_io import is_ot_distribution
    from vimseo.utilities.ot_distribution_io import ot_distribution_to_dict

    if is_ot_distribution(value):
        try:
            return json.loads(
                json.dumps(ot_distribution_to_dict(value), cls=EnhancedJSONEncoder)
            )
        except (ValueError, TypeError):
            return str(value)
    try:
        return EnhancedJSONEncoder().default(value)
    except TypeError:
        return repr(value)


def create_summary(
    tool_name: str,
    tool_run_id: str,
    parent_tool_run_id: str,
    status: str,
    result: BaseResult | None = None,
    error: str = "",
) -> dict[str, Any]:
    """Create the summary of a tool run.

    The summary describes a tool run without its result, so that the runs can be
    searched without loading any result.

    Args:
        tool_name: The name of the tool.
        tool_run_id: The unique identifier of the tool run.
        parent_tool_run_id: The identifier of the run of the tool executing this tool.
        status: The status of the run.
        result: The result of the tool, if any.
        error: The message of the error which ended the run, if any.

    Returns:
        The summary: ``tool_run_id``, ``tool_name``, ``status``, ``parent_tool_run_id``,
        ``datetime``, ``vimseo_version``, plus ``error`` if any, plus
        ``result_class``, the fields of the metadata of the result (``settings``,
        ``simulation_run_ids``, ``child_tool_run_ids``...), ``key_values`` (see
        :meth:`.BaseResult.get_key_values`) and ``model`` if there is a result.
    """
    summary = {
        "tool_run_id": tool_run_id,
        "tool_name": tool_name,
        "status": status,
        "parent_tool_run_id": parent_tool_run_id,
        "datetime": datetime.now().isoformat(" "),
        "vimseo_version": vimseo.__version__,
    }
    if error != "":
        summary["error"] = error
    if result is not None:
        summary["result_class"] = type(result).__name__
        summary.update({
            field.name: getattr(result.metadata, field.name)
            for field in fields(result.metadata)
            if field.name
            not in ("generic", "model", "tool_run_id", "parent_tool_run_id")
        })
        summary["key_values"] = result.get_key_values()
        model = result.metadata.model
        summary["model"] = (
            None
            if model is None
            else {"name": model.name, "load_case": model.load_case.name}
        )
    return summary


def summary_to_json(summary: dict[str, Any]) -> str:
    """Convert the summary of a tool run to JSON, without ever failing.

    Args:
        summary: The summary, see :func:`create_summary`.
    """
    try:
        return json.dumps(summary, indent=2, default=_to_json_value)
    except TypeError:
        # A key which is not a string, in the settings for example.
        return json.dumps(summary, indent=2, default=_to_json_value, skipkeys=True)


class BaseToolArchive(metaclass=GoogleDocstringInheritanceMeta):
    """A base class for the archive of the results of the tools.

    The life of a tool run in the archive is:

    1. :meth:`start_tool_run`, before the tool is executed, so that the simulations
       it launches can be attached to the run,
    2. :meth:`publish_tool_result`, when the tool succeeded, or
       :meth:`end_tool_run` with the status ``"FAILED"`` when it raised.

    The identifiers are the ones described in :mod:`vimseo.core.run_context`: a tool
    run is identified by ``tool_run_id``, and its result lists the ``run_id`` of the
    simulations it used.

    The methods are prefixed by ``tool`` because an archive of tool results can also
    be a model archive (see :class:`.DirectoryToolArchive`).
    """

    STATUS_FINISHED = "FINISHED"
    """The status of a tool run whose result was published."""

    STATUS_FAILED = "FAILED"
    """The status of a tool run which raised."""

    STATUS_RUNNING = "RUNNING"
    """The status of a tool run which has started."""

    @abstractmethod
    def start_tool_run(
        self, tool_name: str, tool_run_id: str, parent_tool_run_id: str = ""
    ) -> None:
        """Start the archive of a tool run.

        Args:
            tool_name: The name of the tool.
            tool_run_id: The unique identifier of the tool run.
            parent_tool_run_id: The identifier of the run of the tool executing this tool.
        """

    @abstractmethod
    def publish_tool_result(self, result: BaseResult) -> None:
        """Publish the result of the current tool run.

        Args:
            result: The result of the tool.
        """

    @abstractmethod
    def end_tool_run(self, status: str, error: str = "") -> None:
        """End the current tool run without a result.

        Args:
            status: The status of the run.
            error: The message of the error which ended the run, if any.
        """

    @abstractmethod
    def get_tool_result(self, tool_run_id: str, tool_name: str = "") -> BaseResult:
        """Return an archived tool result.

        Args:
            tool_run_id: The unique identifier of the tool run.
            tool_name: The name of the tool. If empty, all the tools are searched.

        Raises:
            KeyError: If there is no archived result for this tool run.
        """

    @abstractmethod
    def search_tool_runs(
        self, tool_name: str = "", status: str = ""
    ) -> list[dict[str, object]]:
        """Search the archived tool runs.

        Args:
            tool_name: The name of the tool. If empty, all the tools are searched.
            status: The status of the runs. If empty, all the runs are returned.

        Returns:
            A summary of each run, without its result: ``tool_run_id``,
            ``tool_name``, ``status``, ``result_class``, ``datetime``,
            ``parent_tool_run_id``, ``child_tool_run_ids``, ``simulation_run_ids``,
            ``settings``...
        """

    @abstractmethod
    def find_tool_runs_of_simulation(self, simulation_run_id: str) -> list[str]:
        """Return the tool runs which used a simulation.

        A simulation retrieved from the model cache is used by all the tool runs
        which got it, not only by the one which created it.

        Args:
            simulation_run_id: The ``run_id`` of the simulation.

        Returns:
            The ``tool_run_id`` of the runs.
        """


class NullToolArchive(BaseToolArchive):
    """An archive which archives nothing, to disable the archive of tool results."""

    def start_tool_run(
        self, tool_name: str, tool_run_id: str, parent_tool_run_id: str = ""
    ) -> None:
        """Do nothing."""

    def publish_tool_result(self, result: BaseResult) -> None:
        """Do nothing."""

    def end_tool_run(self, status: str, error: str = "") -> None:
        """Do nothing."""

    def get_tool_result(self, tool_run_id: str, tool_name: str = "") -> BaseResult:
        msg = "The archive of the tool results is disabled."
        raise KeyError(msg)

    def search_tool_runs(
        self, tool_name: str = "", status: str = ""
    ) -> list[dict[str, object]]:
        return []

    def find_tool_runs_of_simulation(self, simulation_run_id: str) -> list[str]:
        return []
