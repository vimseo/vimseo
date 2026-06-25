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

import json
import logging
import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from vimseo.config.global_configuration import _configuration as config
from vimseo.storage_management.base_archive_storage import BaseArchiveManager
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoderArchive

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vimseo.storage_management.base_archive_storage import ArchiveResultType
    from vimseo.storage_management.base_archive_storage import ModelDataType
    from vimseo.storage_management.base_storage_manager import PersistencyPolicy

LOGGER = logging.getLogger(__name__)


class DirectoryArchive(BaseArchiveManager):
    """A database of model results stored in local directories."""

    _RESULTS_JSON_FILE = "results.json"

    def __init__(
        self,
        persistency: PersistencyPolicy,
        model_name,
        load_case_name,
        root_directory: Path | str = "",
        job_name="",
        persistent_file_names=(),
    ):
        super().__init__(persistency, job_name, persistent_file_names)
        self._root_directory = root_directory
        self._experiment_name = (
            config.database.experiment_name
            if config.database.experiment_name != ""
            else f"./{model_name}/{load_case_name}/"
        )
        self._job_directory = ""
        self._accept_overwrite_job_dir = False

    @property
    def root_directory(self) -> str:
        """The root directory where results are stored."""
        return str(self._root_directory.absolute())

    def create_job_directory(self):
        """Create a new job directory."""
        self._job_directory = self._create_job_directory(
            self._root_directory,
            self._job_name,
            self._experiment_name,
        )
        self._current_run_id = self._job_directory

    def set_experiment(self, experiment_name: str):
        self._experiment_name = experiment_name

    def delete_job_directory(self):
        job_dir = self._job_directory
        if self._job_directory != "":
            LOGGER.info(f"Removing job directory: {job_dir}")
            shutil.rmtree(str(job_dir))

    def get_archived_results(self, run_ids: Sequence[str] | Sequence[Path] = ()):

        root_archive = self._root_directory / self._experiment_name
        root_archive = Path(root_archive)

        if not root_archive.is_dir():
            LOGGER.info(
                f"root_archive to be imported is not yet a directory (empty): {root_archive}",
            )
            return None

        if len(run_ids) > 0:
            target_files = run_ids
        else:
            target_files = []
            for root, _, files in os.walk(root_archive):
                if self._RESULTS_JSON_FILE in files:
                    target_files.append(Path(root) / self._RESULTS_JSON_FILE)

        results = [{} for f in target_files]

        for i, file in enumerate(target_files):
            archive_dir = Path(file).parent
            try:
                archive_result = self.get_result(archive_dir)
            except FileNotFoundError as err:  # noqa: BLE001
                msg = f"{err!s} \nError encountered while parsing file {file}"
                raise FileNotFoundError(msg) from err

            # wrap job results in the #i item of the bundle
            results[i] = {
                **archive_result,
                "dir_archive_job": archive_dir,
                "ID": i + 1,
            }

        return results

    def copy_persistent_files(self, src_dir: Path | str) -> None:
        if src_dir == "":
            return

        for file_name in self._persistent_file_names:
            target = src_dir / file_name
            if target.is_file():
                shutil.copy(str(target), str(self._job_directory))
            else:
                LOGGER.warning(
                    f"The file {target} was meant to be copied "
                    f"from the scratch directory to the archive "
                    f"but it was not found."
                )

    def publish(self, archive_result: ArchiveResultType) -> None:
        Path(self._job_directory / self._RESULTS_JSON_FILE).write_text(
            json.dumps(archive_result, cls=EnhancedJSONEncoderArchive)
        )

    def _encode_result(self, archive_result: ArchiveResultType) -> ArchiveResultType:
        """Encode a job result, from ModelResult format to an archived format."""
        return archive_result

    def _decode_result(self, directory_result: ArchiveResultType) -> ModelDataType:
        """Decode a job result, from an archived format, to a ModelResult format."""

        r = deepcopy(directory_result)
        inputs = {k: np.atleast_1d(v) for k, v in r["inputs"].items()}
        outputs = {k: np.atleast_1d(v) for k, v in r["outputs"].items()}
        metadata = {k: np.atleast_1d(v) for k, v in r["metadata"].items()}
        outputs.update(metadata)

        return {"inputs": inputs, "outputs": outputs}

    def get_result(self, archive_dir_path: str | Path = "") -> ModelDataType:
        archive_dir_path = (
            self._job_directory if archive_dir_path == "" else archive_dir_path
        )
        with Path(Path(archive_dir_path) / self._RESULTS_JSON_FILE).open() as f:
            directory_result = json.load(f)
            return self._decode_result(directory_result)
