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
import os
import select
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime
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

    _process: subprocess.Popen | None
    """The subprocess of the job being executed, None outside an execution."""

    stopped_by: str
    """The run limit that terminated the last job: ``"solver_time_limit"``,
    ``"deadline"``, or ``""`` when the job ended on its own."""

    _RUN_LIMIT_POLL_INTERVAL: ClassVar[float] = 0.5
    """The number of seconds between two checks of the run limits."""

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
        self._process = None
        self.stopped_by = ""

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
        """Terminate the external software if it is still running.

        By default, the subprocess and its process group are sent SIGTERM. A subclass
        uses the solver's own way when it has one (e.g. ``abaqus terminate``), which
        writes the results of the increments converged so far.
        """
        process = self._process
        if process is None or process.poll() is not None:
            return
        try:
            if sys.platform.startswith("win"):
                process.terminate()
            else:
                os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def _has_solver_started(self) -> bool:
        """Whether the solver has started, i.e. has written its first convergence file.

        Without convergence sources, the solver is considered started with the
        subprocess.
        """
        sources = self._user_job_options.get(
            "convergence_sources", self._CONVERGENCE_SOURCES
        )
        if not sources:
            return True
        directory = self._convergence_source_directory
        return any((directory / f"{self._job_name}.{ext}").exists() for ext in sources)

    def _check_run_limits(self, solver_start: float | None) -> tuple[float | None, str]:
        """Check the run limits of the user job options.

        Args:
            solver_start: The monotonic time at which the solver was seen started,
                None if not yet.

        Returns:
            The solver start, detected by this check if it was not known,
            and the limit reached, ``""`` if none.
        """
        deadline = self._user_job_options.get("deadline")
        if deadline is not None and datetime.now(deadline.tzinfo) >= deadline:
            return solver_start, "deadline"
        limit = self._user_job_options.get("solver_time_limit", 0.0) or 0.0
        if limit > 0.0:
            if solver_start is None and self._has_solver_started():
                solver_start = time.monotonic()
            if solver_start is not None and time.monotonic() - solver_start >= limit:
                return solver_start, "solver_time_limit"
        return solver_start, ""

    def _enforce_run_limits(self, solver_start: float | None) -> float | None:
        """Terminate the job if a run limit is reached, once.

        Args:
            solver_start: The monotonic time at which the solver was seen started,
                None if not yet.

        Returns:
            The solver start, see :meth:`_check_run_limits`.
        """
        if self.stopped_by:
            return solver_start
        solver_start, reached = self._check_run_limits(solver_start)
        if reached:
            self.stopped_by = reached
            LOGGER.warning(
                "Run limit '%s' reached: terminating the job %s, its results so far "
                "are kept.",
                reached,
                self._job_name,
            )
            self._terminate_external_software()
        return solver_start

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
        self.stopped_by = ""
        solver_start = None
        new_session = not sys.platform.startswith("win")
        if self._is_blocking_subprocess or sys.platform.startswith("win"):
            # the output goes straight to the console; the limits are still enforced
            self._process = proc = subprocess.Popen(
                cmd, cwd=self._job_directory, start_new_session=new_session
            )
            try:
                while True:
                    try:
                        return proc.wait(timeout=self._RUN_LIMIT_POLL_INTERVAL)
                    except subprocess.TimeoutExpired:
                        solver_start = self._enforce_run_limits(solver_start)
            finally:
                self._process = None
        self._process = proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._job_directory,
            text=True,
            start_new_session=new_session,
        )

        self._convergence_cursors = {}
        next_run_limit_check = 0.0
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

                if live_tail and time.monotonic() >= next_convergence_fetch:
                    self._fetch_convergence_safely()
                    next_convergence_fetch = (
                        time.monotonic() + self._CONVERGENCE_POLL_INTERVAL
                    )

                if time.monotonic() >= next_run_limit_check:
                    solver_start = self._enforce_run_limits(solver_start)
                    next_run_limit_check = (
                        time.monotonic() + self._RUN_LIMIT_POLL_INTERVAL
                    )

                if proc.poll() is not None:
                    if activate_convergence_fetching:
                        self._fetch_convergence_safely()
                    time.sleep(1)
                    break

            # Raise an error here if check_subprocess=True:
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

        finally:
            # In any case, restore the original signal handler
            # and kill the subprocess if it is still running
            signal.signal(signal.SIGINT, original_handler)
            if proc.poll() is None:
                LOGGER.warning("Solver still running, killing it...")
                self._terminate_external_software()
            self._process = None

        # Raise an error here if check_subprocess is True:
        if check_subprocess and proc.returncode != 0:
            raise subprocess.CalledProcessError(
                returncode=proc.returncode,
                cmd=cmd,
                output=None,
                stderr=None,
            )

        return proc.returncode
