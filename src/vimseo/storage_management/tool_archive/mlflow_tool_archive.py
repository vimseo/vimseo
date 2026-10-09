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

"""An archive of the results of the tools in MLflow."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from itertools import starmap
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import quote

from mlflow.entities import Metric
from mlflow.entities import Param
from mlflow.entities import RunTag
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

import vimseo
from vimseo.storage_management.mlflow_storage import get_tracking_uri
from vimseo.storage_management.tool_archive.base_tool_archive import BaseToolArchive
from vimseo.storage_management.tool_archive.base_tool_archive import _to_json_value
from vimseo.storage_management.tool_archive.base_tool_archive import create_summary
from vimseo.storage_management.tool_archive.base_tool_archive import summary_to_json
from vimseo.utilities.ot_distribution_io import is_ot_distribution

if TYPE_CHECKING:
    from mlflow.entities import Run

    from vimseo.tools.base_result import BaseResult

LOGGER = logging.getLogger(__name__)

_TAG_PREFIX = "vimseo."
"""The prefix of the tags of the tool runs."""

_MAX_TAG_LENGTH = 5000
"""The maximum length of the value of a tag, below the limits of MLflow."""

_MAX_PARAM_LENGTH = 1000
"""The maximum length of the value of a parameter, below the limits of MLflow."""

_MAX_SIMULATION_LINKS = 50
"""The maximum number of simulations linked from the description of a tool run."""

_SIMULATION_RUN_ID_TAG = "run_id"
"""The tag of the MLflow run of a simulation holding its vimseo ``run_id``."""

_IN_ARTIFACT = "in_artifact"
"""The value of a tag too long for MLflow, whose value is in the summary artifact."""


_MAX_METRICS_PER_BATCH = 1000
"""The maximum number of metrics logged by a single call to MLflow."""


def _to_metric_name(name: str) -> str:
    """Return a name valid for an MLflow metric.

    MLflow accepts letters, digits, underscores, dashes, dots, spaces and slashes:
    the other characters, e.g. the brackets of a component ``x[0]``, are replaced by
    underscores.
    """
    return re.sub(r"[^\w\-. /]", "_", name)


def _tag(name: str) -> str:
    """Return the name of a tag of a tool run."""
    return f"{_TAG_PREFIX}{name}"


class MlflowToolArchive(BaseToolArchive):
    """An archive of the results of the tools in MLflow.

    A tool run is an MLflow run of the experiment :attr:`EXPERIMENT_NAME`, whose name
    is the name of the tool. The run of a subtool is nested in the run of its parent
    tool, so that the MLflow user interface shows the tree of the tool runs::

        tools (experiment)
            DesignValueTool          tags: vimseo.tool_run_id, vimseo.result_class...
                DOETool              params: the settings of the tool
                StatisticsTool       artifacts: {tool_name}_result.hdf5,
                                                {tool_name}_result_metadata.json

    The result is the artifact ``{tool_name}_result.hdf5``, written by
    :meth:`.BaseResult.to_hdf5`, and the summary of the run is the artifact
    ``{tool_name}_result_metadata.json``, as in a :class:`.DirectoryToolArchive`.
    The fields of the summary used to search the runs are also tags, and the settings
    of the tool are parameters, so that MLflow can compare the runs.

    The status of a tool run is the status of its MLflow run. The simulations of the
    tool run are in the archive of their model, with the tag ``tool_run_id``.
    """

    EXPERIMENT_NAME = "tools"
    """The name of the MLflow experiment of the tool runs."""

    SUMMARY_SUFFIX = "_result_metadata.json"
    """The suffix of the name of the artifact of the summary, after the tool name."""

    def __init__(self, root_directory: Path | str = ""):
        """Open an archive.

        Args:
            root_directory: The root directory of a local MLflow database, used when
                the configuration defines no tracking uri (see
                :func:`.get_tracking_uri`).
        """
        self._uri = get_tracking_uri(root_directory)
        self._client = MlflowClient(tracking_uri=self._uri)
        self._experiment_id = ""
        self._tool_name = ""
        self._tool_run_id = ""
        self._parent_run_id = ""
        self._mlflow_run_id = ""

    @property
    def uri(self) -> str:
        """The tracking uri of MLflow."""
        return self._uri

    @property
    def experiment_id(self) -> str:
        """The id of the MLflow experiment of the tool runs, created if needed."""
        if self._experiment_id == "":
            experiment = self._client.get_experiment_by_name(self.EXPERIMENT_NAME)
            self._experiment_id = (
                self._client.create_experiment(self.EXPERIMENT_NAME)
                if experiment is None
                else experiment.experiment_id
            )
        return self._experiment_id

    @staticmethod
    def get_result_file_name(tool_name: str) -> str:
        """Return the name of the artifact of the result of a tool run.

        Args:
            tool_name: The name of the tool.
        """
        from vimseo.tools.base_tool import BaseTool

        return BaseTool.get_result_file_name(tool_name)

    @classmethod
    def get_summary_file_name(cls, tool_name: str) -> str:
        """Return the name of the artifact of the summary of a tool run.

        Args:
            tool_name: The name of the tool.
        """
        return f"{tool_name}{cls.SUMMARY_SUFFIX}"

    def _search_runs(self, filter_string: str = "") -> list[Run]:
        """Return all the MLflow runs of the tool runs matching a filter.

        Searching does not create the experiment of the tool runs.
        """
        if self._experiment_id == "":
            experiment = self._client.get_experiment_by_name(self.EXPERIMENT_NAME)
            if experiment is None:
                return []
            self._experiment_id = experiment.experiment_id
        runs = []
        page_token = None
        while True:
            page = self._client.search_runs(
                [self.experiment_id],
                filter_string=filter_string,
                max_results=1000,
                page_token=page_token,
            )
            runs.extend(page)
            page_token = page.token
            if not page_token:
                return runs

    def _find_run(self, tool_run_id: str, tool_name: str = "") -> Run | None:
        """Return the MLflow run of a tool run, if any."""
        filters = [f"tags.`{_tag('tool_run_id')}` = '{tool_run_id}'"]
        if tool_name:
            filters.append(f"tags.`{_tag('tool_name')}` = '{tool_name}'")
        runs = self._search_runs(" and ".join(filters))
        return runs[0] if runs else None

    def start_tool_run(
        self, tool_name: str, tool_run_id: str, parent_tool_run_id: str = ""
    ) -> None:
        self._tool_name = tool_name
        self._tool_run_id = tool_run_id
        self._parent_run_id = parent_tool_run_id
        tags = {
            _tag("tool_name"): tool_name,
            _tag("tool_run_id"): tool_run_id,
            _tag("parent_tool_run_id"): parent_tool_run_id,
            _tag("vimseo_version"): vimseo.__version__,
        }
        if parent_tool_run_id:
            parent_run = self._find_run(parent_tool_run_id)
            if parent_run is not None:
                # Nests the run in the run of its parent in the user interface.
                tags["mlflow.parentRunId"] = parent_run.info.run_id
        run = self._client.create_run(self.experiment_id, run_name=tool_name, tags=tags)
        self._mlflow_run_id = run.info.run_id

    def publish_tool_result(self, result: BaseResult) -> None:
        summary = create_summary(
            self._tool_name,
            self._tool_run_id,
            self._parent_run_id,
            self.STATUS_FINISHED,
            result=result,
        )
        with TemporaryDirectory() as directory_path:
            directory = Path(directory_path)
            result.to_hdf5(directory / self.get_result_file_name(self._tool_name))
            (directory / self.get_summary_file_name(self._tool_name)).write_text(
                summary_to_json(summary)
            )
            # The artifacts of a result published again replace the former ones.
            self._client.log_artifacts(self._mlflow_run_id, str(directory))

        tags = {_tag("result_class"): summary["result_class"]}
        model = summary["model"]
        if model is not None:
            tags[_tag("model")] = model["name"]
            tags[_tag("load_case")] = model["load_case"]
        for name in ("simulation_run_ids", "child_tool_run_ids"):
            value = json.dumps(list(summary.get(name, ())))
            tags[_tag(name)] = value if len(value) <= _MAX_TAG_LENGTH else _IN_ARTIFACT
        self._client.log_batch(
            self._mlflow_run_id,
            tags=list(starmap(RunTag, tags.items())),
        )

        # The numbers summarizing the result, to sort and compare the runs.
        timestamp = int(time.time() * 1000)
        metrics = [
            Metric(_to_metric_name(name), value, timestamp, 0)
            for name, value in summary.get("key_values", {}).items()
        ]
        for chunk in range(0, len(metrics), _MAX_METRICS_PER_BATCH):
            self._client.log_batch(
                self._mlflow_run_id,
                metrics=metrics[chunk : chunk + _MAX_METRICS_PER_BATCH],
            )

        # The parameters of a run cannot change: a result published again keeps
        # the settings logged the first time.
        if not self._client.get_run(self._mlflow_run_id).data.params:
            params = [
                Param(name, self._to_param_value(value))
                for name, value in summary.get("settings", {}).items()
            ]
            if params:
                self._client.log_batch(self._mlflow_run_id, params=params)

        self._client.set_terminated(self._mlflow_run_id, self.STATUS_FINISHED)
        try:
            self._link_simulations(result)
        except Exception:  # ruff: ignore[blind-except]
            # The links are a convenience of the user interface: the result and
            # its summary are archived anyway.
            LOGGER.exception("The tool run could not be linked to its simulations.")

    def _get_simulation_experiment_ids(self, result: BaseResult) -> list[str]:
        """Return the ids of the MLflow experiments holding the simulations.

        It is the experiment of the model of the result if it is known and in the
        database of this archive, else all the experiments except the one of the
        tool runs: a tool, like a design value, may have no model in its result
        while its subtools ran simulations.
        """
        from vimseo.config.global_configuration import _configuration as config

        model = result.metadata.model
        if model is not None:
            experiment = self._client.get_experiment_by_name(
                config.database.experiment_name
                or f"{model.name}_{model.load_case.name}"
            )
            if experiment is not None:
                return [experiment.experiment_id]
        return [
            experiment.experiment_id
            for experiment in self._client.search_experiments()
            if experiment.name != self.EXPERIMENT_NAME
        ]

    def _get_simulation_runs(self, result: BaseResult) -> dict[str, Run]:
        """Return the MLflow runs of the simulations of a tool result.

        Returns:
            The MLflow runs of the simulations found in the database of this archive,
            bound to their vimseo ``run_id``.
        """
        simulation_run_ids = set(result.metadata.simulation_run_ids)
        if not simulation_run_ids:
            return {}

        experiment_ids = self._get_simulation_experiment_ids(result)
        runs = {}
        page_token = None
        while experiment_ids:
            page = self._client.search_runs(
                experiment_ids, max_results=1000, page_token=page_token
            )
            for run in page:
                simulation_run_id = run.data.tags.get(_SIMULATION_RUN_ID_TAG, "")
                if simulation_run_id in simulation_run_ids:
                    runs[simulation_run_id] = run
            page_token = page.token
            if not page_token:
                break
        if not runs:
            LOGGER.debug(
                f"The simulations of the tool run {self._tool_run_id} are not in the "
                f"MLflow database {self._uri}."
            )
        return runs

    def _add_tool_run_to_simulation(self, run: Run) -> None:
        """Add the current tool run to the tool runs which used a simulation."""
        tag = _tag("tool_run_ids")
        tool_run_ids = json.loads(run.data.tags.get(tag, "[]"))
        if self._tool_run_id in tool_run_ids:
            return
        tool_run_ids.append(self._tool_run_id)
        truncated = False
        while len(json.dumps(tool_run_ids)) > _MAX_TAG_LENGTH:
            # Keep the most recent tool runs.
            tool_run_ids.pop(0)
            truncated = True
        self._client.set_tag(run.info.run_id, tag, json.dumps(tool_run_ids))
        if truncated:
            self._client.set_tag(
                run.info.run_id, _tag("tool_run_ids_truncated"), "true"
            )

    @staticmethod
    def _get_run_link(experiment_id: str, run_id: str) -> str:
        """Return the link to a run in the user interface of MLflow."""
        return f"#/experiments/{experiment_id}/runs/{run_id}"

    def _link_simulations(self, result: BaseResult) -> None:
        """Link the tool run to its simulations and its tool runs, in both ways.

        The description of the MLflow run of the tool run, shown by the user
        interface, links to its parent and child tool runs and to its simulations.
        Each simulation records the tool runs which used it in the tag
        ``vimseo.tool_run_ids``, including the ones which retrieved it from the
        cache of the model.
        """
        simulation_runs = self._get_simulation_runs(result)
        for run in simulation_runs.values():
            self._add_tool_run_to_simulation(run)

        lines = [f"**{self._tool_name}** — tool run `{self._tool_run_id}`", ""]
        run = self._client.get_run(self._mlflow_run_id)
        parent_id = run.data.tags.get("mlflow.parentRunId", "")
        if parent_id:
            lines.append(
                f"- Parent tool run: [{self._parent_run_id}]"
                f"({self._get_run_link(self.experiment_id, parent_id)})"
            )
        children = self._search_runs(
            f"tags.`{_tag('parent_tool_run_id')}` = '{self._tool_run_id}'"
        )
        if children:
            lines.append("- Tool runs of the subtools:")
            lines.extend(
                f"    - [{child.data.tags.get(_tag('tool_name'), '')}]"
                f"({self._get_run_link(self.experiment_id, child.info.run_id)})"
                for child in children
            )

        n_simulations = len(result.metadata.simulation_run_ids)
        if n_simulations:
            lines.append(f"- {n_simulations} simulations")
            if simulation_runs:
                search_filter = quote(
                    f"tags.`{_tag('tool_run_ids')}` LIKE '%{self._tool_run_id}%'"
                )
                experiment_ids = sorted({
                    run.info.experiment_id for run in simulation_runs.values()
                })
                lines.extend(
                    f"    - [all the simulations of this tool run in experiment "
                    f"{self._client.get_experiment(experiment_id).name}]"
                    f"(#/experiments/{experiment_id}?searchFilter={search_filter})"
                    for experiment_id in experiment_ids
                )
                lines.extend(
                    f"    - [{simulation_run_id}]"
                    f"({self._get_run_link(run.info.experiment_id, run.info.run_id)})"
                    for simulation_run_id, run in list(simulation_runs.items())[
                        :_MAX_SIMULATION_LINKS
                    ]
                )
                if len(simulation_runs) > _MAX_SIMULATION_LINKS:
                    lines.append(
                        f"    - ... and {len(simulation_runs) - _MAX_SIMULATION_LINKS}"
                        " more"
                    )
        self._client.set_tag(
            self._mlflow_run_id, "mlflow.note.content", "\n".join(lines)
        )

    @staticmethod
    def _to_param_value(value: Any) -> str:
        """Convert a setting to the value of an MLflow parameter.

        An OpenTURNS distribution is shown by its short form, e.g. ``Normal(mu = 0,
        sigma = 1)``, readable in the user interface of MLflow.
        """
        if is_ot_distribution(value):
            text = str(value)
        else:
            text = json.dumps(value, default=_to_json_value)
        if len(text) > _MAX_PARAM_LENGTH:
            text = f"{text[: _MAX_PARAM_LENGTH - 3]}..."
        return text

    def end_tool_run(self, status: str, error: str = "") -> None:
        if error:
            self._client.set_tag(self._mlflow_run_id, _tag("error"), error[:5000])
        self._client.set_terminated(self._mlflow_run_id, status)

    def get_tool_result(self, tool_run_id: str, tool_name: str = "") -> BaseResult:
        run = self._find_run(tool_run_id, tool_name)
        if run is None:
            msg = (
                f"No archived tool run {tool_run_id}"
                f"{f' of tool {tool_name}' if tool_name else ''} in {self._uri}."
            )
            raise KeyError(msg)
        return self._load_result(run)

    def get_tool_result_of_mlflow_run(self, mlflow_run_id: str) -> BaseResult:
        """Return the tool result archived in an MLflow run.

        Args:
            mlflow_run_id: The id of the MLflow run.

        Raises:
            KeyError: If there is no such MLflow run or it has no result.
        """
        try:
            run = self._client.get_run(mlflow_run_id)
        except MlflowException as error:
            msg = f"No MLflow run {mlflow_run_id} in {self._uri}."
            raise KeyError(msg) from error
        return self._load_result(run)

    def _download_artifact(self, run: Run, file_name: str, directory: str) -> Path:
        """Download an artifact of a run.

        Raises:
            KeyError: If the run has no such artifact.
        """
        try:
            return Path(
                self._client.download_artifacts(run.info.run_id, file_name, directory)
            )
        except (MlflowException, OSError) as error:
            msg = (
                f"The tool run {run.data.tags.get(_tag('tool_run_id'), '')} has no "
                f"{file_name}: its status is {run.info.status}."
            )
            raise KeyError(msg) from error

    def _load_result(self, run: Run) -> BaseResult:
        """Load the result of an MLflow run of a tool run."""
        from vimseo.tools.tool_results_factory import load_result_file

        tool_name = run.data.tags.get(_tag("tool_name"), "")
        with TemporaryDirectory() as directory:
            return load_result_file(
                self._download_artifact(
                    run, self.get_result_file_name(tool_name), directory
                )
            )

    def _read_summary_artifact(self, run: Run) -> dict[str, Any]:
        """Read the summary artifact of a run, or an empty summary if there is none."""
        tool_name = run.data.tags.get(_tag("tool_name"), "")
        with TemporaryDirectory() as directory:
            try:
                path = self._download_artifact(
                    run, self.get_summary_file_name(tool_name), directory
                )
            except KeyError:
                return {}
            return json.loads(path.read_text())

    def _get_summary(self, run: Run) -> dict[str, Any]:
        """Return the summary of a tool run from its MLflow run."""
        tags = run.data.tags
        summary = {
            "tool_run_id": tags.get(_tag("tool_run_id"), ""),
            "tool_name": tags.get(_tag("tool_name"), ""),
            "status": run.info.status,
            "parent_tool_run_id": tags.get(_tag("parent_tool_run_id"), ""),
            "datetime": datetime.fromtimestamp(run.info.start_time / 1000).isoformat(
                " "
            ),
            "vimseo_version": tags.get(_tag("vimseo_version"), ""),
            "settings": dict(run.data.params),
            "key_values": dict(run.data.metrics),
            "mlflow_run_id": run.info.run_id,
            "uri": f"runs:/{run.info.run_id}",
        }
        for name in ("result_class", "error"):
            if _tag(name) in tags:
                summary[name] = tags[_tag(name)]
        if _tag("model") in tags:
            summary["model"] = {
                "name": tags[_tag("model")],
                "load_case": tags.get(_tag("load_case"), ""),
            }
        artifact_summary = None
        for name in ("simulation_run_ids", "child_tool_run_ids"):
            value = tags.get(_tag(name))
            if value is None:
                continue
            if value == _IN_ARTIFACT:
                if artifact_summary is None:
                    artifact_summary = self._read_summary_artifact(run)
                summary[name] = artifact_summary.get(name, [])
            else:
                summary[name] = json.loads(value)
        return summary

    def search_tool_runs(
        self, tool_name: str = "", status: str = ""
    ) -> list[dict[str, object]]:
        filters = []
        if tool_name:
            filters.append(f"tags.`{_tag('tool_name')}` = '{tool_name}'")
        if status:
            filters.append(f"attributes.status = '{status}'")
        runs = sorted(
            self._search_runs(" and ".join(filters)),
            key=lambda run: run.info.start_time,
        )
        return [self._get_summary(run) for run in runs]

    def find_tool_runs_of_simulation(self, simulation_run_id: str) -> list[str]:
        return [
            summary["tool_run_id"]
            for summary in self.search_tool_runs()
            if simulation_run_id in summary.get("simulation_run_ids", ())
        ]
