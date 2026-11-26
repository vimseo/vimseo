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

import pytest

from vimseo.job_executor import abaqus_interactive_executor
from vimseo.job_executor.abaqus_interactive_executor import InteractiveAbaqus


@pytest.mark.parametrize(
    ("job_options", "executable"),
    [
        ({"executable": "abq2024"}, "abq2024"),
        (None, InteractiveAbaqus.DEFAULT_EXECUTABLE),
    ],
)
def test_terminate_external_software(monkeypatch, tmp_path, job_options, executable):
    """Abaqus is terminated with the executable of the job options, else the default."""
    executor = InteractiveAbaqus("cmd")
    executor._job_options = job_options
    executor._job_name = "job"
    executor._job_directory = tmp_path
    calls = []
    monkeypatch.setattr(
        abaqus_interactive_executor.subprocess,
        "run",
        lambda cmd, cwd: calls.append((cmd, cwd)),
    )

    executor._terminate_external_software()

    assert calls == [([executable, "job=job", "terminate"], tmp_path)]
