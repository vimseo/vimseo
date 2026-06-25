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

from dataclasses import dataclass
from dataclasses import fields
from typing import TYPE_CHECKING

from numpy import array
from strenum import StrEnum

if TYPE_CHECKING:
    from numpy import ndarray


@dataclass
class MetaData:
    model: ndarray[str]
    """Name of the model."""

    load_case: ndarray[str]
    """Name of the load_case."""

    error_code: ndarray[int]
    """Code of error of the execution."""

    description: ndarray[str]
    """Free textual description of the current job, for later manual inspection of the
    archive."""

    job_name: ndarray[str]
    """Name of the current job."""

    persistent_result_files: ndarray[str]
    """List of attached persistent result files."""

    n_cpus: ndarray[int]
    """Number of CPUs querried for the execution."""

    date: ndarray[str]
    """Date of the job execution (at termination)."""

    cpu_time: ndarray[float]
    """Execution time of the current job (seconds)."""

    user: ndarray[str]
    """Name of the user who launched the current job."""

    machine: ndarray[str]
    """Name of the user which run the current job."""

    vims_git_version: ndarray[str]
    """VIMSEO version: ID of the git commit checked-out at execution."""

    directory_archive_root: ndarray[str]
    """Path to the archive root directory."""

    directory_archive_job: ndarray[str]
    """Relative path to the current archive folder."""

    directory_scratch_root: ndarray[str]
    """Path to the scratch root directory."""

    directory_scratch_job: ndarray[str]
    """Relative path to the current scratch folder."""


MetaDataNames = StrEnum("MetaDataNames", [field.name for field in fields(MetaData)])


DEFAULT_METADATA = {
    name.value: value
    for name, value in {
        MetaDataNames.model: array(["model"]),
        MetaDataNames.load_case: array(["load_case"]),
        MetaDataNames.error_code: array([-666]),
        MetaDataNames.description: array(["this is a description"]),
        MetaDataNames.job_name: array(["job_name"]),
        MetaDataNames.persistent_result_files: array(["field.vtk", "img.png"]),
        MetaDataNames.n_cpus: array([4]),
        MetaDataNames.date: array(["2025-06-23 14:51:10.350905"]),
        MetaDataNames.cpu_time: array([3600.0]),
        MetaDataNames.user: array(["john.doe"]),
        MetaDataNames.machine: array(["IPF7101"]),
        MetaDataNames.vims_git_version: array(["cdb099aa152e5bf84ad3"]),
        MetaDataNames.directory_archive_root: array(["my_archive/"]),
        MetaDataNames.directory_archive_job: array([
            "my_archive/BendingTestFem/Cantilever/3"
        ]),
        MetaDataNames.directory_scratch_root: array(["my_scratch/"]),
        MetaDataNames.directory_scratch_job: array(["my_scratch/ddc2168sq4c4rr"]),
    }.items()
}
