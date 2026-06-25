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
from abc import abstractmethod
from pathlib import Path

from docstring_inheritance import GoogleDocstringInheritanceMeta
from gemseo.utils.directory_creator import DirectoryCreator
from gemseo.utils.directory_creator import DirectoryNamingMethod
from strenum import StrEnum

LOGGER = logging.getLogger(__name__)


class PersistencyPolicy(StrEnum):
    """The policy of persistency of a job directory, depending on the job status."""

    DELETE_ALWAYS = "DELETE_ALWAYS"
    """Always delete job directory."""

    DELETE_NEVER = "DELETE_NEVER"
    """Never delete job directory."""

    DELETE_IF_SUCCESSFUL = "DELETE_IF_SUCCESSFUL"
    """Delete job directory only if job successful."""

    DELETE_IF_FAULTY = "DELETE_IF_FAULTY"
    """Delete job directory only if job faulty."""


class BaseStorageManager(metaclass=GoogleDocstringInheritanceMeta):
    """File storage system for both scratch and archive."""

    _job_name: str
    """Name of job."""

    _persistency: PersistencyPolicy | None
    """Policy of persistency of job_directory."""

    def __init__(
        self,
        persistency: PersistencyPolicy,
    ):

        self._persistency = persistency
        self._job_directory = ""
        self._directory_naming_method = DirectoryNamingMethod.NUMBERED

    def whether_to_delete(self, job_error_code: int) -> bool:
        """Determine whether the job_directory should be deleted, depending on the
        persistency policy and the job error code.

        Args:
            job_error_code: The error code returned by the job.
        """

        job_is_faulty = job_error_code != 0

        map_policy_to_deletion_enforcement = {
            PersistencyPolicy.DELETE_ALWAYS: True,
            PersistencyPolicy.DELETE_NEVER: False,
            PersistencyPolicy.DELETE_IF_FAULTY: job_is_faulty,
            PersistencyPolicy.DELETE_IF_SUCCESSFUL: not job_is_faulty,
        }
        return map_policy_to_deletion_enforcement[self._persistency]

    def create_job_directory(self):
        """Create the job directory."""

    @property
    def job_directory(self):
        """The directory of the current run."""
        return self._job_directory

    def _create_job_directory(
        self,
        root_directory: Path,
        job_name: str,
        job_dir_prefix: str,
    ) -> Path:
        """Create the job directory."""

        # create root directory
        root_directory.mkdir(parents=True, exist_ok=True)

        # create job directory
        if job_name:
            job_directory = Path(root_directory / job_dir_prefix / job_name)
            try:
                job_directory.mkdir(
                    parents=True, exist_ok=self._accept_overwrite_job_dir
                )
            except FileExistsError as err:
                msg = (
                    f"The job_directory considered for storing results "
                    f"{job_directory} already exists and cannot be overwritten."
                )
                raise FileExistsError(msg) from err

        else:
            job_directory = DirectoryCreator(
                root_directory=root_directory / job_dir_prefix,
                directory_naming_method=self._directory_naming_method,
            ).create()

        return job_directory

    def delete_job_directory(self):
        """Delete the job directory."""

    @abstractmethod
    def enforce_persistency_policy(self, model_result: dict):
        """Apply the persistency."""
