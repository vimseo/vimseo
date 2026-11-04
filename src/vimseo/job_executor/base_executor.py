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

"""A base job executor."""

from __future__ import annotations

import logging
import select
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

import jinja2
from docstring_inheritance import GoogleDocstringInheritanceMeta

from vimseo.job_executor.base_user_job_options import BaseUserJobSettings
from vimseo.job_executor.convergence_log import format_convergence_line
from vimseo.job_executor.convergence_log import is_significant_msg_line
from vimseo.job_executor.convergence_log import tail_new_lines

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

LOGGER = logging.getLogger(__name__)


class JobExecutor(metaclass=GoogleDocstringInheritanceMeta):
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

    _convergence_cursors: dict[str, int]
    """Per convergence-file line cursors, for incremental reads."""

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

    _CONVERGENCE_SOURCES: ClassVar[tuple[str, ...]] = ()
    """The extensions of the ``<job_name>.<ext>`` solver files whose new lines are
    surfaced into the log by :meth:`_fetch_convergence`. Empty means no-op."""

    _CONVERGENCE_POLL_INTERVAL: ClassVar[float] = 2.0
    """The minimum number of seconds between two convergence reads during a solve."""

    def __init__(self, command_template: str):
        self._command_line = ""
        self._n_used_tokens = 0
        self._is_blocking_subprocess = self._IS_BLOCKING_SUBPROCESS
        self._command_template = (
            command_template if command_template != "" else self._COMMAND_TEMPLATE
        )
        self._job_name = ""
        self._job_directory = ""
        self._job_options = None
        self._user_job_options = self._USER_JOB_OPTIONS_MODEL().model_dump()
        self._convergence_cursors = {}

    def execute(
        self,
        check_subprocess: bool = False,
    ):
        """Execute a job.

        Args:
            check_subprocess: Whether to raise an error in case of subprocess failure.
        """
        self._command_line = self._replace_in_command_line(self._command_template)
        cmd = shlex.split(self._command_line)
        LOGGER.info(f"Executing command: {self._command_line}")
        return self._execute_external_software(cmd, check_subprocess)

    def set_options(self, options: BaseUserJobSettings):
        """Set the user job options."""
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

    @property
    def _convergence_source_directory(self) -> Path:
        """The directory :meth:`_fetch_convergence` looks the solver files up in.

        Defaults to the job directory. Job-scheduler executors override this to
        point at the scheduler-side run directory while the job is still
        executing there, before its output files are copied back.
        """
        return Path(self._job_directory)

    def _terminate_external_software(self):
        """Terminate the external software if it is still running."""

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
        """Surface the new lines of the solver convergence files into the log.

        Reads the ``<job_name>.<ext>`` files (for every ``ext`` in the user option
        ``convergence_sources``, defaulting to :attr:`_CONVERGENCE_SOURCES`) located
        in the job directory, and logs the lines written since the previous call.
        Missing, empty or unreadable files are ignored. Any failure is swallowed so
        that convergence fetching can never break a running job.
        """
        sources = self._user_job_options.get(
            "convergence_sources", self._CONVERGENCE_SOURCES
        )
        msg_filter = self._user_job_options.get("convergence_msg_filter", False)
        for ext in sources:
            try:
                path = self._convergence_source_directory / f"{self._job_name}.{ext}"
                new_lines, self._convergence_cursors[ext] = tail_new_lines(
                    path, self._convergence_cursors.get(ext, 0)
                )
                if ext == "msg" and msg_filter:
                    new_lines = [
                        line for line in new_lines if is_significant_msg_line(line)
                    ]
                for line in new_lines:
                    if line.strip():
                        LOGGER.info("%s", format_convergence_line(ext, line))
            except Exception:  # ruff: ignore[blind-except]
                LOGGER.debug(
                    "Convergence fetching failed for '.%s'", ext, exc_info=True
                )

    def _fetch_convergence_safely(self) -> None:
        """Call :meth:`_fetch_convergence`, swallowing any error it may raise."""
        try:
            self._fetch_convergence()
        except Exception:  # ruff: ignore[blind-except]
            LOGGER.debug("Convergence fetching failed", exc_info=True)

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
            start_new_session=True,
        )

        self._convergence_cursors = {}
        live_tail = activate_convergence_fetching and self._user_job_options.get(
            "convergence_live_tail", False
        )
        next_convergence_fetch = 0.0

        # Save the original signal handler and install our own to handle SIGINT (Ctrl+C)
        # gracefully
        original_handler = signal.getsignal(signal.SIGINT)

        def sigint_handler(signum, frame):
            LOGGER.warning("Interrupted, terminating subprocess...")
            # Restore the original signal handler to allow a second Ctrl+C to force
            # kill if needed
            signal.signal(signal.SIGINT, original_handler)
            self._terminate_external_software()

        signal.signal(signal.SIGINT, sigint_handler)

        try:
            while True:
                if proc.stdout.closed or proc.stderr.closed:
                    break
                # wait for event on stdout and/or stderr
                r, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.5)
                for stream in r:
                    # ``readline`` returns a single line.
                    line = stream.readline().rstrip("\n")
                    if not line:
                        continue
                    if stream is proc.stdout:
                        LOGGER.info(line)
                    else:
                        LOGGER.error(line)

                if live_tail and time.monotonic() >= next_convergence_fetch:
                    self._fetch_convergence_safely()
                    next_convergence_fetch = (
                        time.monotonic() + self._CONVERGENCE_POLL_INTERVAL
                    )

                if proc.poll() is not None:
                    if activate_convergence_fetching:
                        self._fetch_convergence_safely()
                    time.sleep(1)
                    break

            # Flush the remaining output. A stream closed while reading it is not
            # read again by ``communicate``, which returns ``None`` for it.
            remaining_stdout, remaining_stderr = proc.communicate()
            for val in (
                remaining_stdout.splitlines() if remaining_stdout is not None else []
            ):
                LOGGER.info(val)
            for val in (
                remaining_stderr.splitlines() if remaining_stderr is not None else []
            ):
                LOGGER.error(val)

        finally:
            # In any case, restore the original signal handler
            # and kill the subprocess if it is still running
            signal.signal(signal.SIGINT, original_handler)
            if proc.poll() is None:
                LOGGER.warning("Solver still running, killing it...")
                self._terminate_external_software()

        # Raise an error here if check_subprocess is True:
        if check_subprocess and proc.returncode != 0:
            raise subprocess.CalledProcessError(
                returncode=proc.returncode,
                cmd=cmd,
                output=None,
                stderr=None,
            )

        return proc.returncode
