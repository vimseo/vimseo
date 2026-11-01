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

"""The archive of the results of the analysis nodes."""

from __future__ import annotations

import json
from abc import abstractmethod
from dataclasses import fields
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from docstring_inheritance import GoogleDocstringInheritanceMeta

import vimseo
from vimseo.storage_management import run_kind
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.analysis_nodes.base_result import BaseResult


def _to_json_value(value: Any) -> Any:
    """Convert a value that :mod:`json` cannot encode, without ever failing.

    The settings of an analysis node can hold any object, like a model. An OpenTURNS
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
    analysis_node_name: str,
    analysis_node_run_id: str,
    parent_analysis_node_run_id: str,
    status: str,
    result: BaseResult | None = None,
    error: str = "",
    study_name: str = "",
) -> dict[str, Any]:
    """Create the summary of an analysis node run.

    The summary describes an analysis node run without its result, so that the runs can be
    searched without loading any result.

    Args:
        analysis_node_name: The name of the analysis node.
        analysis_node_run_id: The unique identifier of the analysis node run.
        parent_analysis_node_run_id: The identifier of the run of the analysis node executing this analysis node.
        status: The status of the run.
        result: The result of the analysis node, if any.
        error: The message of the error which ended the run, if any.
        study_name: The study of the analysis node run.

    Returns:
        The summary: ``analysis_node_run_id``, ``analysis_node_name``, ``status``, ``study_name``,
        ``parent_analysis_node_run_id``,
        ``datetime``, ``vimseo_version``, plus ``error`` if any, plus
        ``result_class``, the fields of the metadata of the result (``settings``,
        ``simulation_run_ids``, ``child_analysis_node_run_ids``...), ``key_values`` (see
        :meth:`.BaseResult.get_key_values`) and ``model`` if there is a result.
    """
    summary = {
        "analysis_node_run_id": analysis_node_run_id,
        "analysis_node_name": analysis_node_name,
        "status": status,
        "study_name": study_name,
        "parent_analysis_node_run_id": parent_analysis_node_run_id,
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
            not in (
                "generic",
                "model",
                "analysis_node_run_id",
                "parent_analysis_node_run_id",
            )
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
    """Convert the summary of an analysis node run to JSON, without ever failing.

    Args:
        summary: The summary, see :func:`create_summary`.
    """
    try:
        return json.dumps(summary, indent=2, default=_to_json_value)
    except TypeError:
        # A key which is not a string, in the settings for example.
        return json.dumps(summary, indent=2, default=_to_json_value, skipkeys=True)


class BaseAnalysisNodeArchive(metaclass=GoogleDocstringInheritanceMeta):
    """A base class for the archive of the results of the analysis nodes.

    The life of an analysis node run in the archive is:

    1. :meth:`start_analysis_node_run`, before the analysis node is executed, so that the simulations
       it launches can be attached to the run,
    2. :meth:`publish_analysis_node_result`, when the analysis node succeeded, or
       :meth:`end_analysis_node_run` with the status ``"FAILED"`` when it raised.

    The identifiers are the ones described in :mod:`vimseo.core.run_context`: an analysis node
    run is identified by ``analysis_node_run_id``, and its result lists the ``run_id`` of the
    simulations it used.

    The methods are prefixed by ``analysis_node`` because an archive of analysis node results can also
    be a model archive (see :class:`.DirectoryAnalysisNodeArchive`).
    """

    STATUS_FINISHED = run_kind.FINISHED
    """The status of an analysis node run whose result was published."""

    STATUS_FAILED = run_kind.FAILED
    """The status of an analysis node run which raised."""

    STATUS_RUNNING = run_kind.RUNNING
    """The status of an analysis node run which has started."""

    _study_name: str = ""
    """The study of the analysis node runs written through this archive manager."""

    @property
    def study_name(self) -> str:
        """The study of the analysis node runs written through this archive manager."""
        return self._study_name

    def set_study_name(self, study_name: str) -> None:
        """Set the study of the next analysis node runs.

        Args:
            study_name: The study.
        """
        self._study_name = study_name

    @abstractmethod
    def start_analysis_node_run(
        self,
        analysis_node_name: str,
        analysis_node_run_id: str,
        parent_analysis_node_run_id: str = "",
    ) -> None:
        """Start the archive of an analysis node run.

        Args:
            analysis_node_name: The name of the analysis node.
            analysis_node_run_id: The unique identifier of the analysis node run.
            parent_analysis_node_run_id: The identifier of the run of the analysis node executing this analysis node.
        """

    @abstractmethod
    def publish_analysis_node_result(self, result: BaseResult) -> None:
        """Publish the result of the current analysis node run.

        Args:
            result: The result of the analysis node.
        """

    @abstractmethod
    def end_analysis_node_run(self, status: str, error: str = "") -> None:
        """End the current analysis node run without a result.

        Args:
            status: The status of the run.
            error: The message of the error which ended the run, if any.
        """

    @abstractmethod
    def get_analysis_node_result(
        self, analysis_node_run_id: str, analysis_node_name: str = ""
    ) -> BaseResult:
        """Return an archived analysis node result.

        Args:
            analysis_node_run_id: The unique identifier of the analysis node run.
            analysis_node_name: The name of the analysis node. If empty, all the analysis nodes are searched.

        Raises:
            KeyError: If there is no archived result for this analysis node run.
        """

    @abstractmethod
    def search_analysis_node_runs(
        self, analysis_node_name: str = "", status: str = "", study_name: str = ""
    ) -> list[dict[str, object]]:
        """Search the archived analysis node runs.

        Args:
            analysis_node_name: The name of the analysis node. If empty, all the analysis nodes are searched.
            status: The status of the runs. If empty, all the runs are returned.
            study_name: The study of the runs. If empty, all the studies are
                searched.

        Returns:
            A summary of each run, without its result: ``analysis_node_run_id``,
            ``analysis_node_name``, ``status``, ``result_class``, ``datetime``,
            ``parent_analysis_node_run_id``, ``child_analysis_node_run_ids``, ``simulation_run_ids``,
            ``settings``...
        """

    @abstractmethod
    def find_analysis_node_runs_of_simulation(
        self, simulation_run_id: str
    ) -> list[str]:
        """Return the analysis node runs which used a simulation.

        A simulation retrieved from the model cache is used by all the analysis node runs
        which got it, not only by the one which created it.

        Args:
            simulation_run_id: The ``run_id`` of the simulation.

        Returns:
            The ``analysis_node_run_id`` of the runs.
        """


class NullAnalysisNodeArchive(BaseAnalysisNodeArchive):
    """An archive which archives nothing, to disable the archive of analysis node results."""

    def start_analysis_node_run(
        self,
        analysis_node_name: str,
        analysis_node_run_id: str,
        parent_analysis_node_run_id: str = "",
    ) -> None:
        """Do nothing."""

    def publish_analysis_node_result(self, result: BaseResult) -> None:
        """Do nothing."""

    def end_analysis_node_run(self, status: str, error: str = "") -> None:
        """Do nothing."""

    def get_analysis_node_result(
        self, analysis_node_run_id: str, analysis_node_name: str = ""
    ) -> BaseResult:
        msg = "The archive of the analysis node results is disabled."
        raise KeyError(msg)

    def search_analysis_node_runs(
        self, analysis_node_name: str = "", status: str = "", study_name: str = ""
    ) -> list[dict[str, object]]:
        return []

    def find_analysis_node_runs_of_simulation(
        self, simulation_run_id: str
    ) -> list[str]:
        return []
