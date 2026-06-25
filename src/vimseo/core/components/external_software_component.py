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
import subprocess
from typing import TYPE_CHECKING

from gemseo.core.discipline.discipline import Discipline

from vimseo.core.base_component import BaseComponent
from vimseo.job_executor.base_executor import JobExecutor

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.material.material import Material

LOGGER = logging.getLogger(__name__)


class ExternalSoftwareComponent(BaseComponent):
    """A component to execute an external software."""

    _check_subprocess: bool
    """If ``True``, raise an error if the subprocess fails.

    Otherwise, log a warning with the standard and error outputs of the subprocess.
    """

    _attached_files: list
    """A list of files that are copied to the job directory."""

    _job_executor: JobExecutor
    """A job executor."""

    auto_detect_grammar_files = True
    default_cache_type = Discipline.CacheType.HDF5
    default_grammar_type = Discipline.GrammarType.JSON

    def __init__(
        self,
        load_case_name: str = "",
        material_grammar_file: Path | str = "",
        material: Material | None = None,
        check_subprocess: bool = False,
    ) -> None:
        super().__init__(load_case_name, material_grammar_file, material)
        self._job_executor = JobExecutor("")
        self._check_subprocess = check_subprocess
        self._attached_files = []

    @property
    def job_executor(self) -> JobExecutor:
        return self._job_executor

    def _check_job_completion(self) -> int:
        """Checks a completion criterion after execution of the subprocess.

        Returns: The return code of the subprocess result.
        """
        return 0

    def _check_subprocess_completion(
        self,
        error_subprocess: int,
        check: bool,
        cmd: str,
    ) -> int:
        """Check subprocess completion.

        Args:
            error_subprocess: The error code from the
                ``JobExecutor._execute_external_software`` method.
            check: Whether the subprocess raises an error if it fails.
            cmd: The subprocess command.

        Returns: The error code.
        """
        if error_subprocess == 0:
            error_subprocess = self._check_job_completion()

        if error_subprocess != 0:
            if check:
                LOGGER.error(f"Subprocess returned an error: {error_subprocess}")
                raise subprocess.CalledProcessError(
                    returncode=error_subprocess,
                    cmd=cmd,
                    stderr=subprocess.STDOUT,
                )

            LOGGER.warning("Subprocess returned an error which is ignored")

        return error_subprocess

    def add_attached_files(self, files_to_attach: list[str, Path]) -> None:
        """Add files to be copied to job directory.

        Args:
            files_to_attach: A list of files to be copied to the job directory.

        Returns:
        """
        for f in files_to_attach:
            self._attached_files.append(f)

    def _copy_attached_files_to_job_directory(self) -> None:
        """Copy attached files to job directory."""
        for file in self._attached_files:
            shutil.copy(str(file), str(self._job_directory))
