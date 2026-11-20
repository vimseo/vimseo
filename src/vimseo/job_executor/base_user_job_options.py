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

"""The user job options for all job executors."""

from __future__ import annotations

from datetime import datetime  # ruff: ignore[typing-only-standard-library-import]

from pydantic import Field

from vimseo.analysis_nodes.base_settings import BaseSettings


class BaseUserJobSettings(BaseSettings):
    """The base user job options."""

    n_cpus: int = Field(
        default=1, description="The number of CPUs used by the external software."
    )
    executable: str = Field(
        default="", description="The path to the executable of the external software."
    )
    job_name: str = Field(
        default="", description="The job name used for the job directory."
    )
    solver_time_limit: float = Field(
        default=0.0,
        ge=0.0,
        description="The maximum time (s) given to the solver, 0 meaning no limit. "
        "The time is counted from the start of the solver, detected by the first "
        "convergence file it writes (see ``convergence_sources``), so that a wait in a "
        "licence queue does not count; without convergence sources, it is counted from "
        "the start of the subprocess. A job reaching the limit is terminated, its results "
        "so far are kept and the run is reported as faulty.",
    )
    deadline: datetime | None = Field(
        default=None,
        description="The wall-clock time at which the job is terminated, whatever its "
        "progress, e.g. the end of a licence lending; None meaning no deadline. The "
        "results so far are kept and the run is reported as faulty.",
    )
