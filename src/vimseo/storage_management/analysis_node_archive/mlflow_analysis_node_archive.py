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

"""An archive of the results of the analysis nodes in MLflow."""

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
from vimseo.storage_management import run_kind
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    BaseAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    _to_json_value,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    create_summary,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    summary_to_json,
)
from vimseo.storage_management.mlflow_storage import get_tracking_uri
from vimseo.utilities.ot_distribution_io import is_ot_distribution

if TYPE_CHECKING:
    from mlflow.entities import Run

    from vimseo.analysis_nodes.base_result import BaseResult

LOGGER = logging.getLogger(__name__)

_TAG_PREFIX = "vimseo."
"""The prefix of the tags of the analysis node runs."""

_MAX_TAG_LENGTH = 5000
"""The maximum length of the value of a tag, below the limits of MLflow."""

_MAX_PARAM_LENGTH = 1000
"""The maximum length of the value of a parameter, below the limits of MLflow."""

_MAX_SIMULATION_LINKS = 50
"""The maximum number of simulations linked from the description of an analysis node run."""

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
    """Return the name of a tag of an analysis node run."""
    return f"{_TAG_PREFIX}{name}"


class MlflowAnalysisNodeArchive(BaseAnalysisNodeArchive):
    """An archive of the results of the analysis nodes in MLflow.

    An analysis node run is an MLflow run of the experiment of its study, next to the
    simulations of the study, with the tag ``vimseo.kind=analysis_node_run``; its name is the
    name of the analysis node. The run of a sub-analysis node is nested in the run of its parent analysis node, so
    that the MLflow user interface shows the tree of the analysis node runs::

        {study} (experiment)
            DesignValueAnalysisNode          tags: vimseo.analysis_node_run_id, vimseo.result_class...
                DOEAnalysisNode              params: the settings of the analysis node
                StatisticsAnalysisNode       artifacts: {analysis_node_name}_result.hdf5,
                                                {analysis_node_name}_result_metadata.json

    The result is the artifact ``{analysis_node_name}_result.hdf5``, written by
    :meth:`.BaseResult.to_hdf5`, and the summary of the run is the artifact
    ``{analysis_node_name}_result_metadata.json``, as in a :class:`.DirectoryAnalysisNodeArchive`.
    The fields of the summary used to search the runs are also tags, and the settings
    of the analysis node are parameters, so that MLflow can compare the runs.

    The status of an analysis node run is the status of its MLflow run. The simulations of the
    analysis node run are in the archive of their model, with the tag ``analysis_node_run_id``.
    """

    SUMMARY_SUFFIX = "_result_metadata.json"
    """The suffix of the name of the artifact of the summary, after the analysis node name."""

    def __init__(self, root_directory: Path | str = "", study_name: str = ""):
        """Open an archive.

        Args:
            root_directory: The root directory of a local MLflow database (see
                :func:`.get_tracking_uri`).
            study_name: The study of the analysis node runs written through this archive.
                If empty, the one of the configuration.
        """
        from vimseo.config.global_configuration import _configuration as config

        self._study_name = study_name or config.study_name
        self._uri = get_tracking_uri(root_directory)
        self._client = MlflowClient(tracking_uri=self._uri)
        self._experiment_id = ""
        self._analysis_node_name = ""
        self._analysis_node_run_id = ""
        self._parent_run_id = ""
        self._mlflow_run_id = ""

    @property
    def uri(self) -> str:
        """The tracking uri of MLflow."""
        return self._uri

    def set_study_name(self, study_name: str) -> None:
        super().set_study_name(study_name)
        self._experiment_id = ""

    @property
    def experiment_id(self) -> str:
        """The id of the MLflow experiment of the study, created if needed."""
        if self._experiment_id == "":
            experiment = self._client.get_experiment_by_name(self._study_name)
            self._experiment_id = (
                self._client.create_experiment(self._study_name)
                if experiment is None
                else experiment.experiment_id
            )
        return self._experiment_id

    @staticmethod
    def get_result_file_name(analysis_node_name: str) -> str:
        """Return the name of the artifact of the result of an analysis node run.

        Args:
            analysis_node_name: The name of the analysis node.
        """
        from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode

        return BaseAnalysisNode.get_result_file_name(analysis_node_name)

    @classmethod
    def get_summary_file_name(cls, analysis_node_name: str) -> str:
        """Return the name of the artifact of the summary of an analysis node run.

        Args:
            analysis_node_name: The name of the analysis node.
        """
        return f"{analysis_node_name}{cls.SUMMARY_SUFFIX}"

    def _search_runs(
        self, filter_string: str = "", study_name: str | None = ""
    ) -> list[Run]:
        """Return all the MLflow runs of the analysis node runs matching a filter.

        Searching creates no experiment.

        Args:
            filter_string: The filter of the runs, ANDed with the kind of run.
            study_name: The study of the runs. If empty, all the studies; if ``None``,
                the current study.
        """
        if study_name == "":
            experiment_ids = [
                experiment.experiment_id
                for experiment in self._client.search_experiments()
            ]
        else:
            experiment = self._client.get_experiment_by_name(
                self._study_name if study_name is None else study_name
            )
            experiment_ids = [] if experiment is None else [experiment.experiment_id]
        if not experiment_ids:
            return []
        filters = [f"tags.`{run_kind.KIND_TAG}` = '{run_kind.ANALYSIS_NODE_RUN}'"]
        if filter_string:
            filters.append(filter_string)
        runs = []
        page_token = None
        while True:
            page = self._client.search_runs(
                experiment_ids,
                filter_string=" and ".join(filters),
                max_results=1000,
                page_token=page_token,
            )
            runs.extend(page)
            page_token = page.token
            if not page_token:
                return runs

    def _find_run(
        self, analysis_node_run_id: str, analysis_node_name: str = ""
    ) -> Run | None:
        """Return the MLflow run of an analysis node run, if any."""
        filters = [f"tags.`{_tag('analysis_node_run_id')}` = '{analysis_node_run_id}'"]
        if analysis_node_name:
            filters.append(
                f"tags.`{_tag('analysis_node_name')}` = '{analysis_node_name}'"
            )
        runs = self._search_runs(" and ".join(filters))
        return runs[0] if runs else None

    def start_analysis_node_run(
        self,
        analysis_node_name: str,
        analysis_node_run_id: str,
        parent_analysis_node_run_id: str = "",
    ) -> None:
        self._analysis_node_name = analysis_node_name
        self._analysis_node_run_id = analysis_node_run_id
        self._parent_run_id = parent_analysis_node_run_id
        tags = {
            _tag("analysis_node_name"): analysis_node_name,
            _tag("analysis_node_run_id"): analysis_node_run_id,
            _tag("parent_analysis_node_run_id"): parent_analysis_node_run_id,
            _tag("vimseo_version"): vimseo.__version__,
            run_kind.KIND_TAG: run_kind.ANALYSIS_NODE_RUN,
            run_kind.STUDY_TAG: self._study_name,
        }
        if parent_analysis_node_run_id:
            parent_run = self._find_run(parent_analysis_node_run_id)
            if parent_run is not None:
                # Nests the run in the run of its parent in the user interface.
                tags["mlflow.parentRunId"] = parent_run.info.run_id
        run = self._client.create_run(
            self.experiment_id, run_name=analysis_node_name, tags=tags
        )
        self._mlflow_run_id = run.info.run_id

    def publish_analysis_node_result(self, result: BaseResult) -> None:
        summary = create_summary(
            self._analysis_node_name,
            self._analysis_node_run_id,
            self._parent_run_id,
            self.STATUS_FINISHED,
            result=result,
            study_name=self._study_name,
        )
        with TemporaryDirectory() as directory_path:
            directory = Path(directory_path)
            result.to_hdf5(
                directory / self.get_result_file_name(self._analysis_node_name)
            )
            (
                directory / self.get_summary_file_name(self._analysis_node_name)
            ).write_text(summary_to_json(summary))
            # The artifacts of a result published again replace the former ones.
            self._client.log_artifacts(self._mlflow_run_id, str(directory))

        tags = {_tag("result_class"): summary["result_class"]}
        model = summary["model"]
        if model is not None:
            tags[_tag("model")] = model["name"]
            tags[_tag("load_case")] = model["load_case"]
        for name in ("simulation_run_ids", "child_analysis_node_run_ids"):
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
            LOGGER.exception(
                "The analysis node run could not be linked to its simulations."
            )

    def _get_simulation_experiment_ids(self, result: BaseResult) -> list[str]:
        """Return the ids of the MLflow experiments holding the simulations.

        It is the experiment of the current study if it exists, else all the
        experiments: the simulations of an analysis node run may come, through the cache of the
        model, from another study.
        """
        experiment = self._client.get_experiment_by_name(self._study_name)
        if experiment is not None:
            return [experiment.experiment_id]
        return [
            experiment.experiment_id for experiment in self._client.search_experiments()
        ]

    def _get_simulation_runs(self, result: BaseResult) -> dict[str, Run]:
        """Return the MLflow runs of the simulations of an analysis node result.

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
                experiment_ids,
                filter_string=f"tags.`{run_kind.KIND_TAG}` = '{run_kind.SIMULATION}'",
                max_results=1000,
                page_token=page_token,
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
                f"The simulations of the analysis node run {self._analysis_node_run_id} are not in the "
                f"MLflow database {self._uri}."
            )
        return runs

    def _add_analysis_node_run_to_simulation(self, run: Run) -> None:
        """Add the current analysis node run to the analysis node runs which used a simulation."""
        tag = _tag("analysis_node_run_ids")
        analysis_node_run_ids = json.loads(run.data.tags.get(tag, "[]"))
        if self._analysis_node_run_id in analysis_node_run_ids:
            return
        analysis_node_run_ids.append(self._analysis_node_run_id)
        truncated = False
        while len(json.dumps(analysis_node_run_ids)) > _MAX_TAG_LENGTH:
            # Keep the most recent analysis node runs.
            analysis_node_run_ids.pop(0)
            truncated = True
        self._client.set_tag(run.info.run_id, tag, json.dumps(analysis_node_run_ids))
        if truncated:
            self._client.set_tag(
                run.info.run_id, _tag("analysis_node_run_ids_truncated"), "true"
            )

    @staticmethod
    def _get_run_link(experiment_id: str, run_id: str) -> str:
        """Return the link to a run in the user interface of MLflow."""
        return f"#/experiments/{experiment_id}/runs/{run_id}"

    def _link_simulations(self, result: BaseResult) -> None:
        """Link the analysis node run to its simulations and its analysis node runs, in both ways.

        The description of the MLflow run of the analysis node run, shown by the user
        interface, links to its parent and child analysis node runs and to its simulations.
        Each simulation records the analysis node runs which used it in the tag
        ``vimseo.analysis_node_run_ids``, including the ones which retrieved it from the
        cache of the model.
        """
        simulation_runs = self._get_simulation_runs(result)
        for run in simulation_runs.values():
            self._add_analysis_node_run_to_simulation(run)

        lines = [
            f"**{self._analysis_node_name}** — analysis node run `{self._analysis_node_run_id}`",
            "",
        ]
        run = self._client.get_run(self._mlflow_run_id)
        parent_id = run.data.tags.get("mlflow.parentRunId", "")
        if parent_id:
            lines.append(
                f"- Parent analysis node run: [{self._parent_run_id}]"
                f"({self._get_run_link(self.experiment_id, parent_id)})"
            )
        children = self._search_runs(
            f"tags.`{_tag('parent_analysis_node_run_id')}` = '{self._analysis_node_run_id}'",
            None,
        )
        if children:
            lines.append("- Analysis node runs of the sub-analysis nodes:")
            lines.extend(
                f"    - [{child.data.tags.get(_tag('analysis_node_name'), '')}]"
                f"({self._get_run_link(self.experiment_id, child.info.run_id)})"
                for child in children
            )

        n_simulations = len(result.metadata.simulation_run_ids)
        if n_simulations:
            lines.append(f"- {n_simulations} simulations")
            if simulation_runs:
                search_filter = quote(
                    f"tags.`{_tag('analysis_node_run_ids')}` LIKE '%{self._analysis_node_run_id}%'"
                )
                experiment_ids = sorted({
                    run.info.experiment_id for run in simulation_runs.values()
                })
                lines.extend(
                    f"    - [all the simulations of this analysis node run in experiment "
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

    def end_analysis_node_run(self, status: str, error: str = "") -> None:
        if error:
            self._client.set_tag(self._mlflow_run_id, _tag("error"), error[:5000])
        self._client.set_terminated(self._mlflow_run_id, status)

    def get_analysis_node_result(
        self, analysis_node_run_id: str, analysis_node_name: str = ""
    ) -> BaseResult:
        run = self._find_run(analysis_node_run_id, analysis_node_name)
        if run is None:
            msg = (
                f"No archived analysis node run {analysis_node_run_id}"
                f"{f' of analysis node {analysis_node_name}' if analysis_node_name else ''} in {self._uri}."
            )
            raise KeyError(msg)
        return self._load_result(run)

    def get_analysis_node_result_of_mlflow_run(self, mlflow_run_id: str) -> BaseResult:
        """Return the analysis node result archived in an MLflow run.

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
                f"The analysis node run {run.data.tags.get(_tag('analysis_node_run_id'), '')} has no "
                f"{file_name}: its status is {run.info.status}."
            )
            raise KeyError(msg) from error

    def _load_result(self, run: Run) -> BaseResult:
        """Load the result of an MLflow run of an analysis node run."""
        from vimseo.analysis_nodes.analysis_node_results_factory import load_result_file

        analysis_node_name = run.data.tags.get(_tag("analysis_node_name"), "")
        with TemporaryDirectory() as directory:
            return load_result_file(
                self._download_artifact(
                    run, self.get_result_file_name(analysis_node_name), directory
                )
            )

    def _read_summary_artifact(self, run: Run) -> dict[str, Any]:
        """Read the summary artifact of a run, or an empty summary if there is none."""
        analysis_node_name = run.data.tags.get(_tag("analysis_node_name"), "")
        with TemporaryDirectory() as directory:
            try:
                path = self._download_artifact(
                    run, self.get_summary_file_name(analysis_node_name), directory
                )
            except KeyError:
                return {}
            return json.loads(path.read_text())

    def _get_summary(self, run: Run) -> dict[str, Any]:
        """Return the summary of an analysis node run from its MLflow run."""
        tags = run.data.tags
        summary = {
            "analysis_node_run_id": tags.get(_tag("analysis_node_run_id"), ""),
            "analysis_node_name": tags.get(_tag("analysis_node_name"), ""),
            "status": run.info.status,
            "study_name": tags.get(run_kind.STUDY_TAG, ""),
            "parent_analysis_node_run_id": tags.get(
                _tag("parent_analysis_node_run_id"), ""
            ),
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
        for name in ("simulation_run_ids", "child_analysis_node_run_ids"):
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

    def search_analysis_node_runs(
        self, analysis_node_name: str = "", status: str = "", study_name: str = ""
    ) -> list[dict[str, object]]:
        filters = []
        if analysis_node_name:
            filters.append(
                f"tags.`{_tag('analysis_node_name')}` = '{analysis_node_name}'"
            )
        if status:
            filters.append(f"attributes.status = '{status}'")
        runs = sorted(
            self._search_runs(" and ".join(filters), study_name),
            key=lambda run: run.info.start_time,
        )
        return [self._get_summary(run) for run in runs]

    def find_analysis_node_runs_of_simulation(
        self, simulation_run_id: str
    ) -> list[str]:
        return [
            summary["analysis_node_run_id"]
            for summary in self.search_analysis_node_runs()
            if simulation_run_id in summary.get("simulation_run_ids", ())
        ]
