# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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
from collections.abc import Mapping
from copy import deepcopy
from numbers import Number
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote
from urllib.parse import urlparse

import mlflow
import numpy as np
import urllib3
from mlflow import delete_run
from numpy import atleast_1d
from numpy import ndarray

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.certificates import MLFLOW_CERTIFICATES_DIR
from vimseo.storage_management.directory_storage import BaseArchiveManager
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vimseo.storage_management.base_storage_manager import PersistencyPolicy
    from vimseo.storage_management.directory_storage import ArchiveResultType
    from vimseo.storage_management.directory_storage import ModelDataType

LOGGER = logging.getLogger(__name__)

INPUT_PREFIX = "inputs."

MlflowArchiveResultType = Mapping[str, Mapping[str, ndarray | Number | str]]


class MlflowArchive(BaseArchiveManager):
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

        if config.database.mode == "Team":
            self._uri = config.database.team_uri
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

        elif config.database.mode == "Local":
            # TODO use root_directory instead of config.database.local_uri
            self._uri = (
                config.database.local_uri
                if config.database.local_uri != ""
                else f"file:///{Path(root_directory).absolute()!s}"
            )
        else:
            msg = f"Wrong value for config.database.mode: {config.database.mode}"
            raise ValueError(msg)

        mlflow.set_tracking_uri(self._uri)
        self._experiment_name = (
            config.database.experiment_name
            if config.database.experiment_name != ""
            else f"{self._model_name}_{self._load_case_name}"
        )
        self._mlflow_client = mlflow.tracking.MlflowClient()
        mlflow.set_experiment(self._experiment_name)

    @property
    def uri(self) -> str:
        """The Mlflow database uri."""
        return self._uri

    @property
    def root_directory(self) -> str:
        """The database uri."""
        return f"{self._uri}"

    def set_experiment(
        self, experiment_name: str, tags: Mapping[str, str] | None = None
    ):
        tags = {} if tags is None else tags
        mlflow.set_experiment(experiment_name)
        self._experiment_name = experiment_name
        mlflow.set_experiment_tags(tags)

    def get_archived_results(self, run_ids: Sequence[str] = ()):

        run_ids = (
            run_ids
            if len(run_ids) > 0
            else mlflow.search_runs(experiment_names=[self._experiment_name])["run_id"]
        )

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

    def copy_persistent_files(self, src_dir):
        if src_dir == "":
            return

        for file_name in self._persistent_file_names:
            target = src_dir / file_name
            if target.is_file():
                mlflow.log_artifact(target, run_id=self._current_run_id)
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

        with mlflow.start_run(run_name=self._job_name) as run:
            self._current_run_id = run.info.run_id
            mlflow.set_tags(tags)
            mlflow.log_params(
                prepare_data(
                    dict(arrays_real, **arrays_non_real, **strings_), jsonify=True
                )
            )
            mlflow.log_metrics(prepare_data(floats))
            mlflow.log_metric(
                MetaDataNames.cpu_time,
                archive_result["metadata"][MetaDataNames.cpu_time],
            )
            for name, value in arrays_real.items():
                for i, v in enumerate(value):
                    mlflow.log_metric(
                        (
                            name
                            if name in archive_result["outputs"]
                            else f"inputs.{name}"
                        ),
                        v,
                        step=i,
                    )

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

    def get_result(self, run_id: str = "") -> ModelDataType:
        run = self._mlflow_client.get_run(
            run_id if run_id != "" else self._current_run_id
        )
        self._job_directory = Path(unquote(urlparse(run.info.artifact_uri).path))

        result = self._decode_result(run.data.to_dictionary())
        result["outputs"][MetaDataNames.directory_archive_job] = atleast_1d(
            str(self._job_directory)
        )
        return result

    def delete_job_directory(self):
        delete_run(self._current_run_id)
