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

import logging
import shutil
from typing import TYPE_CHECKING

from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.base_storage_manager import BaseStorageManager

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.storage_management.base_storage_manager import PersistencyPolicy

LOGGER = logging.getLogger(__name__)


class DirectoryScratch(BaseStorageManager):
    def __init__(
        self,
        root_directory: Path,
        persistency: PersistencyPolicy,
        job_name,
        model_name,
        load_case_name,
    ):

        super().__init__(persistency)
        self._root_directory = root_directory
        self._job_name = job_name
        self._experiment_name = f"./{model_name}/{load_case_name}/"
        self._accept_overwrite_job_dir = True
        self._job_directory = ""

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

    def delete_job_directory(self):
        if self._job_directory != "":
            LOGGER.info(f"Removing job directory: {self._job_directory}")
            shutil.rmtree(str(self._job_directory))

    def enforce_persistency_policy(self, model_result: dict):
        if self.whether_to_delete(model_result["outputs"][MetaDataNames.error_code][0]):
            self.delete_job_directory()
