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
"""Tests of the run limits of the job executors: solver time limit and deadline."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from datetime import timedelta

import pytest

from vimseo.job_executor.abaqus_interactive_executor import InteractiveAbaqus
from vimseo.job_executor.base_executor import JobExecutor
from vimseo.job_executor.base_user_job_options import BaseUserJobSettings

_LOGGER_NAME = "vimseo.job_executor.base_executor"

pytestmark = pytest.mark.skip_under_windows


class _StubExecutor(JobExecutor):
    """A non-blocking executor whose solver writes a status file."""

    _IS_BLOCKING_SUBPROCESS = False
    _CONVERGENCE_SOURCES = ("sta",)
    _RUN_LIMIT_POLL_INTERVAL = 0.1


class _BlockingStubExecutor(_StubExecutor):
    """The same executor, with a blocking subprocess."""

    _IS_BLOCKING_SUBPROCESS = True


def _solver(delay_before_sta: float, duration: float) -> list[str]:
    """A fake solver: waits for its licences, writes its status file, then solves."""
    return [
        "sh",
        "-c",
        f"sleep {delay_before_sta}; echo inc 1 >> job.sta; sleep {duration}; exit 0",
    ]


@pytest.fixture(params=[_StubExecutor, _BlockingStubExecutor])
def executor(request, tmp_path):
    """A stub executor, non-blocking then blocking, in a temporary job directory."""
    job_executor = request.param("")
    job_executor._job_directory = tmp_path
    job_executor._job_name = "job"
    return job_executor


def test_options_defaults():
    """Without limits, the options are inactive."""
    options = BaseUserJobSettings()
    assert options.solver_time_limit == pytest.approx(0.0)
    assert options.deadline is None


def test_negative_solver_time_limit_is_rejected():
    """The solver time limit cannot be negative."""
    with pytest.raises(ValueError, match="solver_time_limit"):
        BaseUserJobSettings(solver_time_limit=-1.0)


def test_no_limit_lets_the_job_end(executor):
    """Without limits the job runs to its end and is not reported as stopped."""
    returncode = executor._execute_external_software(
        _solver(0.0, 0.3), check_subprocess=False
    )

    assert returncode == 0
    assert executor.stopped_by == ""


def test_solver_time_limit_terminates_the_job(executor, caplog):
    """A job solving longer than the limit is terminated and reported as such."""
    executor._user_job_options["solver_time_limit"] = 0.3
    start = time.monotonic()

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        returncode = executor._execute_external_software(
            _solver(0.0, 30.0), check_subprocess=False
        )

    assert time.monotonic() - start < 5.0
    assert returncode != 0
    assert executor.stopped_by == "solver_time_limit"
    assert "Run limit 'solver_time_limit' reached" in caplog.text


def test_solver_time_limit_does_not_count_the_queue(executor):
    """The time before the solver writes its status file does not count."""
    executor._user_job_options["solver_time_limit"] = 0.6
    # 0.8 s in the "licence queue", then 0.3 s of solving: within the limit
    returncode = executor._execute_external_software(
        _solver(0.8, 0.3), check_subprocess=False
    )

    assert returncode == 0
    assert executor.stopped_by == ""


def test_deadline_terminates_the_job(executor, caplog):
    """A job still running at the deadline is terminated, queued or not."""
    executor._user_job_options["solver_time_limit"] = 0.0
    executor._user_job_options["deadline"] = datetime.now() + timedelta(seconds=0.4)
    start = time.monotonic()

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        # the solver is still "in the queue" at the deadline
        returncode = executor._execute_external_software(
            _solver(30.0, 1.0), check_subprocess=False
        )

    assert time.monotonic() - start < 5.0
    assert returncode != 0
    assert executor.stopped_by == "deadline"
    assert "Run limit 'deadline' reached" in caplog.text


def test_stopped_by_is_reset_by_the_next_execution(executor):
    """The report of a stop belongs to one execution."""
    executor._user_job_options["solver_time_limit"] = 0.2
    executor._execute_external_software(_solver(0.0, 30.0), check_subprocess=False)
    assert executor.stopped_by == "solver_time_limit"

    executor._user_job_options["solver_time_limit"] = 0.0
    executor._execute_external_software(_solver(0.0, 0.1), check_subprocess=False)

    assert executor.stopped_by == ""


def test_abaqus_terminate_command(monkeypatch, tmp_path):
    """The Abaqus executor terminates its job with ``abaqus terminate``."""
    calls = []
    monkeypatch.setattr(
        "vimseo.job_executor.abaqus_interactive_executor.subprocess.run",
        lambda cmd, **kwargs: calls.append((cmd, kwargs)),
    )
    executor = InteractiveAbaqus("")
    executor._set_job_options(tmp_path)
    executor._job_name = "job_1"

    executor._terminate_external_software()

    assert calls == [
        (["abq2022", "job=job_1", "terminate"], {"cwd": tmp_path, "check": False})
    ]
