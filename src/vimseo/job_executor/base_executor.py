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

"""A base job executor."""

from __future__ import annotations

import logging
import select
import subprocess
import sys
import time
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

import jinja2
from docstring_inheritance import GoogleDocstringInheritanceMeta

from vimseo.job_executor.base_user_job_options import BaseUserJobSettings

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class BaseJobExecutor(metaclass=GoogleDocstringInheritanceMeta):
    """A base job executor."""

    _is_blocking_subprocess: bool
    """Whether the subprocess running the command is blocking."""

    _command_line: str
    """The executed command."""

    _n_used_tokens: int
    """The number of necessary license tokens."""

    _job_name: str
    """The job name."""

    _job_directory: str | Path
    """The job directory."""

    _convergence_log_length: int
    """The current number of lines of the convergence log."""

    _job_options: dict | None
    """The full job options.

    Except the user job options, they are only known at model execution.
    """

    _user_job_options: Mapping[str, Any]
    """The user job options."""

    _COMMAND_TEMPLATE: ClassVar[str] = ""
    """The template used to generate the executed command line."""

    DEFAULT_EXECUTABLE = ""
    """The default executable name."""

    _IS_BLOCKING_SUBPROCESS = False
    """Whether the subprocess running the command is blocking."""

    _USER_JOB_OPTIONS_MODEL: ClassVar[BaseUserJobSettings] = BaseUserJobSettings
    """The pydantic model of the user job options."""

    def __init__(self, command_template: str):
        self._command_line = ""
        self._n_used_tokens = 0
        self._is_blocking_subprocess = self._IS_BLOCKING_SUBPROCESS
        self._command_template = (
            command_template if command_template != "" else self._COMMAND_TEMPLATE
        )
        self._job_name = ""
        self._job_directory = ""
        self._convergence_log_length = 0
        self._job_options = None
        self._user_job_options = self._USER_JOB_OPTIONS_MODEL().model_dump()

    def execute(
        self,
        check_subprocess: bool = False,
    ):
        """Execute a job.

        Args:
            check_subprocess: Whether to raise an error in case of subprocess failure.
        """
        self._command_line = self._replace_in_command_line(self._command_template)
        return self._execute_external_software(
            self._command_line.split(), check_subprocess
        )

    def set_options(self, options: BaseUserJobSettings):
        if not isinstance(options, self._USER_JOB_OPTIONS_MODEL):
            msg = f"options must be of type {self._USER_JOB_OPTIONS_MODEL}"
            raise TypeError(msg)
        self._user_job_options = options.model_dump()

    def _set_job_options(self, job_directory: Path):
        """Set the job options."""
        self._job_directory = job_directory
        options = self._user_job_options
        options.update({"executable": self.DEFAULT_EXECUTABLE})
        self._job_options = options
        self._job_name = options.get("job_name", "")

    @property
    def options(self) -> dict:
        return self._user_job_options

    @property
    def command_line(self):
        return self._command_line

    @classmethod
    def _render_template(
        cls, template: str, substitution_dict: Mapping[str, Any]
    ) -> str:
        """Format a string thanks to jinja2.

        Args :
            template: A string to format (with jinja syntax).
            substitution_dict: A dictionary mapping the names of the variables,
            to the value that should be placed instead.
        Returns: The formatted string.
        """
        environment = jinja2.Environment()
        template_jinja = environment.from_string(template)

        return template_jinja.render(**substitution_dict)

    def _replace_in_command_line(self, template_command: str) -> str:
        """Generates the command line that will launch the RUN Abaqus subprocess.

        Args:
            template_command: The command template.

        Returns:
            The command line.
        """
        return self._render_template(
            template_command,
            self._job_options,
        )

    def _fetch_convergence(self) -> None:
        """Fetch the log of simulation convergence."""

    def _execute_external_software(
        self,
        cmd: Sequence[str],
        check_subprocess: bool,
        activate_convergence_fetching: bool = True,
    ) -> int:
        """Execute a subprocess.

        Args:
            cmd: The subprocess command.
            check_subprocess: Whether to check and raise an error if the subprocess fails.

        Returns: The error code.
        """
        if self._is_blocking_subprocess or sys.platform.startswith("win"):
            return subprocess.run(cmd, cwd=self._job_directory).returncode
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._job_directory,
            text=True,
        )
        self._convergence_log_length = 0
        while True:
            # wait for event on stdout and/or stderr
            r, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.5)
            for stream in r:
                if stream is proc.stdout:
                    line = stream.readline()
                    if line:
                        for val in line.splitlines():
                            LOGGER.info(val)
                elif stream is proc.stderr:
                    line = stream.readline()
                    if line:
                        for val in line.splitlines():
                            LOGGER.error(val)

            if activate_convergence_fetching:
                self._fetch_convergence()
                time.sleep(1)

            if proc.poll() is not None:
                if activate_convergence_fetching:
                    self._fetch_convergence()
                time.sleep(1)
                break

        # Last bit of stuff, flushing the buffers eventually
        remaining_stdout, remaining_stderr = proc.communicate()
        for val in (
            remaining_stdout.splitlines() if remaining_stdout is not None else []
        ):
            LOGGER.info(val)
        for val in (
            remaining_stderr.splitlines() if remaining_stderr is not None else []
        ):
            LOGGER.error(val)

        # Raise an error here if check_subprocess=True:
        if check_subprocess and proc.returncode != 0:
            raise subprocess.CalledProcessError(
                returncode=proc.returncode,
                cmd=cmd,
                output=proc.stdout,
                stderr=proc.stderr,
            )

        return proc.returncode
