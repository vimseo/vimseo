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

import collections
import json
import logging
import os
import time
from collections.abc import Mapping
from copy import deepcopy
from itertools import starmap
from numbers import Number
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import url2pathname

import mlflow
import numpy as np
import urllib3
from mlflow.entities import Metric
from mlflow.entities import Param
from mlflow.entities import RunTag
from numpy import atleast_1d
from numpy import ndarray

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.certificates import MLFLOW_CERTIFICATES_DIR
from vimseo.storage_management.directory_storage import BaseArchiveManager
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence

    from vimseo.storage_management.base_storage_manager import PersistencyPolicy
    from vimseo.storage_management.directory_storage import ArchiveResultType
    from vimseo.storage_management.directory_storage import ModelDataType

LOGGER = logging.getLogger(__name__)

INPUT_PREFIX = "inputs."

MlflowArchiveResultType = Mapping[str, Mapping[str, ndarray | Number | str]]

# Limits of a single ``MlflowClient.log_batch`` call.
_MAX_PARAMS_OR_TAGS_PER_BATCH = 100
_MAX_METRICS_PER_BATCH = 1000


def _chunks(items: Sequence, size: int) -> Iterable[Sequence]:
    """Split a sequence in consecutive chunks of at most ``size`` items."""
    for start in range(0, len(items), size):
        yield items[start : start + size]


def get_tracking_uri(root_directory: Path | str = "") -> str:
    """Return the tracking uri of MLflow from the configuration.

    In ``Team`` mode, the credentials of the tracking server are also set in the
    environment.

    Args:
        root_directory: The root directory of a local database, used in ``Local``
            mode when the configuration defines no ``local_uri``.

    Returns:
        The tracking uri.

    Raises:
        ValueError: If the mode of the database is unknown.
    """
    if config.database.mode == "Team":
        os.environ["MLFLOW_TRACKING_USERNAME"] = config.database.username
        os.environ["MLFLOW_TRACKING_PASSWORD"] = config.database.password
        os.environ["REQUESTS_CA_BUNDLE"] = (
            config.database.ssl_certificate_file
            if config.database.ssl_certificate_file != ""
            else str((MLFLOW_CERTIFICATES_DIR / "irt_certificate.txt").absolute())
        )
        if config.database.use_insecure_tls == "True":
            os.environ["MLFLOW_TRACKING_DATABASE_USE_INSECURE_TLS"] = "true"
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return config.database.team_uri

    if config.database.mode == "Local":
        # TODO use root_directory instead of config.database.local_uri
        return (
            config.database.local_uri
            if config.database.local_uri != ""
            else f"file:///{Path(root_directory).absolute()!s}"
        )

    msg = f"Wrong value for config.database.mode: {config.database.mode}"
    raise ValueError(msg)


class MlflowArchive(BaseArchiveManager):
    """A database of model results stored in an MLFlow tracking backend."""

    _current_run_id: str

    _RESULTS_JSON_FILE = "results.json"

    def __init__(
        self,
        persistency: PersistencyPolicy,
        root_directory: Path | str = "",
        job_name="",
        model_name="",
        load_case_name="",
        persistent_file_names=(),
    ):

        super().__init__(persistency, job_name, persistent_file_names)
        self._root_directory = root_directory
        self._model_name = model_name
        self._load_case_name = load_case_name

        self._uri = get_tracking_uri(root_directory)

        # This archive only relies on a client bound to its own tracking uri, and
        # never on the fluent API of MLflow (``mlflow.set_tracking_uri``,
        # ``mlflow.search_runs``, ``mlflow.set_experiment``...), which reads a state
        # shared by the whole process: another archive with another uri would
        # overwrite it. A script which queries the database with the fluent API must
        # set the uri itself: ``mlflow.set_tracking_uri(archive_manager.uri)``.
        self._mlflow_client = mlflow.tracking.MlflowClient(tracking_uri=self._uri)
        self._experiment_name = (
            config.database.experiment_name
            if config.database.experiment_name != ""
            else f"{self._model_name}_{self._load_case_name}"
        )
        # The experiment is created with the first run, so that opening the archive
        # to read it does not create an empty experiment.
        self._run_is_open = False

    @property
    def uri(self) -> str:
        """The Mlflow database uri."""
        return self._uri

    @property
    def root_directory(self) -> str:
        """The database uri."""
        return f"{self._uri}"

    def _get_or_create_experiment_id(self, experiment_name: str) -> str:
        """Return the id of an experiment, that is created if it does not exist."""
        experiment = self._mlflow_client.get_experiment_by_name(experiment_name)
        if experiment is None:
            return self._mlflow_client.create_experiment(experiment_name)
        return experiment.experiment_id

    def set_experiment(
        self, experiment_name: str, tags: Mapping[str, str] | None = None
    ):
        tags = {} if tags is None else tags
        experiment_id = self._get_or_create_experiment_id(experiment_name)
        self._experiment_name = experiment_name
        for name, value in tags.items():
            self._mlflow_client.set_experiment_tag(experiment_id, name, value)

    def _search_finished_run_ids(self) -> list[str]:
        """Return the ids of the finished runs of the current experiment."""
        experiment_id = self._get_or_create_experiment_id(self._experiment_name)
        run_ids = []
        page_token = None
        while True:
            runs = self._mlflow_client.search_runs(
                [experiment_id],
                # A run is created at the beginning of the job (see
                # ``create_job_directory``): skip the ones that are still running,
                # were aborted, or have no results.
                filter_string="attributes.status = 'FINISHED'",
                max_results=1000,
                page_token=page_token,
            )
            run_ids.extend(run.info.run_id for run in runs)
            page_token = runs.token
            if not page_token:
                return run_ids

    def get_archived_results(self, run_ids: Sequence[str] = ()):

        run_ids = run_ids if len(run_ids) > 0 else self._search_finished_run_ids()

        if len(run_ids) == 0:
            LOGGER.info(
                f"No results found in archive {self._experiment_name}",
            )
            return ()

        return [
            {
                **self.get_result(run_id),
                "dir_archive_job": self._experiment_name,
                "ID": i + 1,
            }
            for i, run_id in enumerate(run_ids)
        ]

    @staticmethod
    def _artifact_directory(run) -> Path:
        """The local path of the artifact directory of a run."""
        # ``url2pathname`` handles the drive letter of Windows paths: a plain
        # ``unquote`` of the url path gives an invalid ``\C:\...``.
        return Path(url2pathname(urlparse(run.info.artifact_uri).path))

    def _terminate_run(self, status: str) -> None:
        """Terminate the current run with the given status."""
        self._mlflow_client.set_terminated(self._current_run_id, status)
        self._run_is_open = False

    def create_job_directory(self):
        """Create the MLflow run of the current job.

        The run is created before the job is executed, and not when its results
        are published, for two independent reasons:

        - ``job_directory``, the directory of the artifacts of the run (the persistent
          files such as fields, which are files and not database entries), is known
          when the metadata is generated. The metadata ``directory_archive_job`` is
          then correct in the outputs returned by ``execute``, in the model cache and
          in the run, and not only when the run is read back with ``get_result``.
          It is the local path of the machine which ran the job.
        - A run exists when a persistency policy asks to delete the job, so the run
          deleted is the current one, and not the previous one.
        """
        if self._run_is_open:
            LOGGER.warning(
                f"Run {self._current_run_id} is still open: it has neither been "
                "published nor deleted. Marking it as failed."
            )
            self._terminate_run("FAILED")

        run = self._mlflow_client.create_run(
            self._get_or_create_experiment_id(self._experiment_name),
            run_name=self._job_name or None,
        )
        self._current_run_id = run.info.run_id
        self._run_is_open = True
        self._job_directory = self._artifact_directory(run)

    def abort_job(self):
        if self._run_is_open:
            self._terminate_run("FAILED")

    def copy_persistent_files(self, src_dir):
        # No run when the job was deleted under the persistency policy. An empty
        # run id must not reach MLflow, which would create a new run.
        if src_dir == "" or self._current_run_id == "":
            return

        for file_name in self._persistent_file_names:
            target = src_dir / file_name
            if target.is_file():
                self._mlflow_client.log_artifact(self._current_run_id, str(target))
            else:
                LOGGER.warning(
                    f"The file {target} was meant to be stored to "
                    f"from the scratch directory to the archive but "
                    f"it was not found."
                )

    def publish(self, archive_result: ArchiveResultType) -> None:

        def extract_floats(data):
            floats = {}
            arrays_non_real = {}
            arrays_real = {}
            strings_ = {}
            for name, value in data.items():
                if isinstance(value, str):
                    strings_.update({name: value})
                elif isinstance(value, (collections.abc.Sequence, np.ndarray)):
                    if all(np.isreal(value)):
                        arrays_real.update({name: value})
                    else:
                        arrays_non_real.update({name: value})
                else:
                    floats.update({name: value})
            return floats, arrays_real, arrays_non_real, strings_

        all_data = deepcopy(archive_result["inputs"])
        all_data.update(archive_result["outputs"])
        floats, arrays_real, arrays_non_real, strings_ = extract_floats(all_data)

        tags = {
            name: value
            for name, value in archive_result["metadata"].items()
            if name
            not in [MetaDataNames.persistent_result_files, MetaDataNames.cpu_time]
        }
        tags.update({
            MetaDataNames.persistent_result_files: json.dumps(
                archive_result["metadata"][MetaDataNames.persistent_result_files],
                cls=EnhancedJSONEncoder,
            )
        })

        def prepare_data(data: dict, jsonify: bool = False):
            return {
                (name if name in archive_result["outputs"] else f"inputs.{name}"): (
                    json.dumps(v, cls=EnhancedJSONEncoder) if jsonify else v
                )
                for name, v in data.items()
            }

        def key(name: str) -> str:
            return name if name in archive_result["outputs"] else f"inputs.{name}"

        if not self._run_is_open:
            # ``publish`` called without a previous ``create_job_directory``.
            self.create_job_directory()

        timestamp = int(time.time() * 1000)
        run_tags = [RunTag(name, str(value)) for name, value in tags.items()]
        run_params = list(
            starmap(
                Param,
                prepare_data(
                    dict(arrays_real, **arrays_non_real, **strings_), jsonify=True
                ).items(),
            )
        )
        run_metrics = [
            Metric(name, float(value), timestamp, 0)
            for name, value in prepare_data(floats).items()
        ]
        run_metrics.append(
            Metric(
                MetaDataNames.cpu_time,
                float(archive_result["metadata"][MetaDataNames.cpu_time]),
                timestamp,
                0,
            )
        )
        for name, value in arrays_real.items():
            run_metrics.extend(
                Metric(key(name), float(v), timestamp, i) for i, v in enumerate(value)
            )

        run_id = self._current_run_id
        for chunk in _chunks(run_tags, _MAX_PARAMS_OR_TAGS_PER_BATCH):
            self._mlflow_client.log_batch(run_id, tags=chunk)
        for chunk in _chunks(run_params, _MAX_PARAMS_OR_TAGS_PER_BATCH):
            self._mlflow_client.log_batch(run_id, params=chunk)
        for chunk in _chunks(run_metrics, _MAX_METRICS_PER_BATCH):
            self._mlflow_client.log_batch(run_id, metrics=chunk)
        self._terminate_run("FINISHED")

    def _decode_result(self, results_archive: ArchiveResultType) -> ModelDataType:
        """Decode an archived result to a ModelResult format."""

        inputs = {}
        outputs = {}
        for name, value in results_archive["metrics"].items():
            if name.startswith(INPUT_PREFIX):
                inputs.update({name.split(INPUT_PREFIX)[1]: atleast_1d(value)})
            else:
                outputs.update({name: atleast_1d(value)})
        for name, value in results_archive["params"].items():
            if name.startswith(INPUT_PREFIX):
                inputs.update({
                    name.split(INPUT_PREFIX)[1]: atleast_1d(json.loads(value))
                })
            else:
                outputs.update({name: atleast_1d(json.loads(value))})

        tags = results_archive["tags"]
        for name in [MetaDataNames.n_cpus, MetaDataNames.error_code]:
            tags[name] = int(tags[name])
        tags[MetaDataNames.cpu_time] = float(
            results_archive["metrics"][MetaDataNames.cpu_time]
        )

        outputs.update({
            name: atleast_1d(value)
            for name, value in tags.items()
            if name in [name.value for name in MetaDataNames]
            and name != MetaDataNames.persistent_result_files
        })
        outputs.update({
            MetaDataNames.persistent_result_files: atleast_1d(
                json.loads(
                    results_archive["tags"][MetaDataNames.persistent_result_files]
                )
            )
        })

        return {"inputs": inputs, "outputs": outputs}

    def get_results_by_run_id(self, run_ids: Iterable[str]) -> list[ModelDataType]:
        from vimseo.storage_management.base_archive_storage import _order_results

        run_ids = list(run_ids)
        # The simulations of all the experiments, except the one of the tool runs.
        experiment_ids = [
            experiment.experiment_id
            for experiment in self._mlflow_client.search_experiments()
            if experiment.name != "tools"
        ]
        found = {}
        for run_id in dict.fromkeys(run_ids):
            runs = self._mlflow_client.search_runs(
                experiment_ids,
                filter_string=f"tags.{MetaDataNames.run_id} = '{run_id}'",
                max_results=1,
            )
            if runs:
                found[run_id] = self.get_result(runs[0].info.run_id)
        return _order_results(run_ids, found, self._uri)

    def get_result(self, run_id: str = "") -> ModelDataType:
        run = self._mlflow_client.get_run(
            run_id if run_id != "" else self._current_run_id
        )
        self._job_directory = self._artifact_directory(run)

        result = self._decode_result(run.data.to_dictionary())
        result["outputs"][MetaDataNames.directory_archive_job] = atleast_1d(
            str(self._job_directory)
        )
        return result

    def delete_job_directory(self):
        if self._current_run_id == "":
            return
        self._mlflow_client.delete_run(self._current_run_id)
        self._current_run_id = ""
        self._run_is_open = False
