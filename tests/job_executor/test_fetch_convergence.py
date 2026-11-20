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

import pytest

from vimseo.job_executor.abaqus_interactive_executor import InteractiveAbaqus

_LOGGER_NAME = "vimseo.job_executor.base_executor"


@pytest.fixture
def executor(tmp_path):
    """An Abaqus executor pointed at a temporary job directory."""
    job_executor = InteractiveAbaqus("cmd")
    job_executor._job_directory = tmp_path
    job_executor._job_name = "job"
    return job_executor


def test_new_lines_of_every_source_are_surfaced(executor, tmp_path, caplog):
    """The new lines of each configured convergence file are logged with a prefix."""
    (tmp_path / "job.sta").write_text("inc 1\ninc 2\n")
    (tmp_path / "job.msg").write_text("residual 1e-3\n")
    executor.update_options(convergence_msg_filter=False)

    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        executor._fetch_convergence()

    assert "SOLVER[sta] ▓▓ inc 1" in caplog.text
    assert "SOLVER[sta] ▓▓ inc 2" in caplog.text
    assert "[solver msg] residual 1e-3" in caplog.text
    assert executor._convergence_cursors == {"sta": 2, "msg": 1}


def test_second_call_only_logs_new_lines(executor, tmp_path, caplog):
    """A second call does not repeat the lines already surfaced."""
    sta = tmp_path / "job.sta"
    sta.write_text("inc 1\n")
    executor._fetch_convergence()

    sta.write_text("inc 1\ninc 2\n")
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        executor._fetch_convergence()

    assert "SOLVER[sta] ▓▓ inc 2" in caplog.text
    assert "SOLVER[sta] ▓▓ inc 1" not in caplog.text


def test_convergence_sources_option_is_honored(executor, tmp_path, caplog):
    """Only the files listed in ``convergence_sources`` are read."""
    (tmp_path / "job.sta").write_text("inc 1\n")
    (tmp_path / "job.msg").write_text("residual 1e-3\n")
    executor.update_options(convergence_sources=["msg"], convergence_msg_filter=False)

    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        executor._fetch_convergence()

    assert "[solver msg] residual 1e-3" in caplog.text
    assert "sta" not in caplog.text
    assert executor._convergence_cursors == {"msg": 1}


def test_missing_files_are_silent(executor, caplog):
    """No convergence file at all is not an error."""
    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        executor._fetch_convergence()

    assert caplog.text == ""


def test_msg_filter_keeps_only_significant_lines(executor, tmp_path, caplog):
    """With ``convergence_msg_filter`` only warning/error/... lines of .msg are logged."""
    (tmp_path / "job.msg").write_text(
        " ***WARNING: SOLVER PROBLEM\n AVERAGE FORCE 65.7\n"
    )
    executor.update_options(convergence_sources=["msg"], convergence_msg_filter=True)

    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        executor._fetch_convergence()

    assert "[solver msg]  ***WARNING: SOLVER PROBLEM" in caplog.text
    assert "AVERAGE FORCE" not in caplog.text


def test_live_tail_is_on_by_default_for_abaqus():
    """``InteractiveAbaqus`` surfaces convergence during the solve by default."""
    assert InteractiveAbaqus("cmd").options["convergence_live_tail"] is True
