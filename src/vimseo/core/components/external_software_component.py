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

import logging
import shutil
import subprocess
from typing import TYPE_CHECKING

from numpy import atleast_1d

from vimseo.core.components.base_component import BaseComponent
from vimseo.core.model_metadata import MetaDataNames
from vimseo.job_executor.base_executor import BaseJobExecutor

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.core.load_case import LoadCase
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

    _job_executor: BaseJobExecutor
    """A job executor."""

    def __init__(
        self,
        load_case: LoadCase | None = None,
        material_grammar_file: Path | str = "",
        material: Material | None = None,
        check_subprocess: bool = False,
    ) -> None:
        super().__init__(load_case, material_grammar_file, material, check_subprocess)

        self.output_grammar.update_from_data({"error_code": atleast_1d(0)})
        self.output_grammar.required_names.add("error_code")

        self._job_executor = BaseJobExecutor("")
        self._attached_files = []

    @property
    def job_executor(self) -> BaseJobExecutor:
        return self._job_executor

    @property
    def n_cpus(self):
        """The number of CPUs used to run the external software."""
        return self._job_executor.options["n_cpus"]

    def write_input_files(self, input_data):
        """Write the input files for the external software."""

    def pre_run(self, input_data):
        """Pre-run operations."""

    def post_run(self, input_data, output_data):
        """Post-run operations."""

    def _run(self, input_data):
        """Run the external software."""

        self.pre_run(input_data)

        self.write_input_files(input_data)

        self._job_executor._set_job_options(
            self.job_directory,
        )
        error_run = self._job_executor.execute(
            check_subprocess=self._check_subprocess,
        )
        error_run = 0
        if error_run:
            LOGGER.warning(
                f"An error has occurred in {self.__class__.__name__}, "
                f"running command {self._job_executor._command_line}."
            )

        error_run = 0
        error_run = self._check_subprocess_completion(
            error_run, self._check_subprocess, self._job_executor.command_line.split()
        )

        if error_run:
            LOGGER.warning(
                f"An error has occurred in {self.__class__.__name__}, "
                f"in check subprocess completion."
            )

        output_data = {}
        self.post_run(input_data, output_data)
        output_data[MetaDataNames.error_code] = atleast_1d(error_run)

        return output_data

    def set_job_executor(self, job_executor: BaseJobExecutor):
        """Set the job executor.

        Args:
            job_executor: The job executor.
        """
        self._job_executor = job_executor

    def _is_successful_execution(self) -> int:
        """Checks a completion criterion after execution of the subprocess.

        Returns: The return code of the subprocess result.
        """
        return True

    def _check_subprocess_completion(
        self,
        error_subprocess: int,
        check: bool,
        cmd: str,
    ) -> int:
        """Check subprocess completion.

        Args:
            error_subprocess: The error code from the
                ``BaseJobExecutor._execute_external_software`` method.
            check: Whether the subprocess raises an error if it fails.
            cmd: The subprocess command.

        Returns: The error code.
        """
        if error_subprocess == 0:
            error_subprocess = int(not self._is_successful_execution())

        if error_subprocess != 0:
            if check:
                LOGGER.error(f"Subprocess returned an error: {error_subprocess}")
                raise subprocess.CalledProcessError(
                    returncode=error_subprocess,
                    cmd=cmd,
                    stderr=subprocess.STDOUT,
                )

            LOGGER.warning(
                "Subprocess returned an error which is ignored "
                "(``check_subprocess=False``)."
            )

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
