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

import subprocess
from pathlib import Path

import pytest

from vimseo.config.global_configuration import _configuration as config
from vimseo.utilities.pytest_conftest import *  # ruff: ignore[unused-import, undefined-local-with-import-star]
from vimseo.utilities.pytest_conftest import (
    pytest_sessionfinish as _fortran_sessionfinish,
)
from vimseo.utilities.pytest_conftest import (
    pytest_sessionstart as _fortran_sessionstart,
)

# os.environ["VIMS_PROJECT_DIRECTORY"] = os.path.dirname(__file__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_baseline_untracked: set[str] = set()


def _untracked_files() -> set[str]:
    """Return the paths git reports as untracked ("??"), or an empty set if git is
    unusable (no git binary, or the tree is not a git checkout)."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {line[3:] for line in result.stdout.splitlines() if line.startswith("??")}


def pytest_sessionstart(session):
    """Snapshot the untracked files before the run, in addition to the fortran
    stdout/stderr workaround from ``pytest_conftest``."""
    _fortran_sessionstart(session)
    if not hasattr(session.config, "workerinput"):
        global _baseline_untracked
        _baseline_untracked = _untracked_files()


def pytest_sessionfinish(session, exitstatus):
    """Fail the run if the test suite left untracked files in the repository.

    This catches tests that write to a cwd-relative path instead of using the
    ``tmp_wd`` fixture. Only the xdist controller (or a non-parallel run) does the
    comparison, once, after every worker has finished.
    """
    _fortran_sessionfinish(session)
    if hasattr(session.config, "workerinput"):
        return
    new_files = _untracked_files() - _baseline_untracked
    if new_files:
        message = (
            "The test suite left untracked files in the repository -- a test wrote "
            "to a cwd-relative path instead of using the `tmp_wd` fixture:\n"
            + "\n".join(f"  {f}" for f in sorted(new_files))
        )
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line(message, red=True, bold=True)
        else:
            print(message)
        session.exitstatus = 1


@pytest.fixture(autouse=True)
def no_tool_archive():
    """Disable the archive of the tool results, so that a test does not write into the
    directory it runs in.

    A test of the archive enables it by passing ``archive_manager`` to the tool,
    which takes precedence over the configuration.
    """
    previous = config.tool_archive_manager
    config.tool_archive_manager = "none"
    yield
    config.tool_archive_manager = previous
