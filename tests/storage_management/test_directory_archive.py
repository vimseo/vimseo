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

from pathlib import Path

import pytest

from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.storage_management.directory_storage import DirectoryArchive


@pytest.fixture
def archive(tmp_path):
    """A directory archive rooted in a temporary directory."""
    return DirectoryArchive(
        PersistencyPolicy.DELETE_ALWAYS,
        "MockModel",
        "LC1",
        root_directory=tmp_path,
    )


def test_uri_and_experiment_and_run_name(archive, tmp_path):
    """The base archive manager exposes uri, experiment and run-name accessors."""
    assert archive.uri == str(tmp_path)

    archive.set_experiment("my_experiment")
    assert archive.experiment_name == "my_experiment"

    archive.set_run_name("my_run")
    assert archive.run_name == "my_run"


def test_encode_result_is_identity(archive):
    """The directory archive stores results without re-encoding them."""
    result = {"inputs": {"x": 1.0}, "outputs": {"y": 2.0}, "metadata": {}}
    assert archive._encode_result(result) == result


def test_get_archived_results_on_empty_archive_returns_none(archive):
    """Querying an archive with no stored result returns ``None``."""
    assert archive.get_archived_results() is None


def test_copy_persistent_files_warns_when_missing(tmp_path, caplog):
    """A persistent file that cannot be found is warned about, not copied."""
    archive = DirectoryArchive(
        PersistencyPolicy.DELETE_ALWAYS,
        "MockModel",
        "LC1",
        root_directory=tmp_path,
        persistent_file_names=["missing.txt"],
    )
    archive._job_directory = tmp_path
    archive.copy_persistent_files(Path(tmp_path))
    assert "was not found" in caplog.text
