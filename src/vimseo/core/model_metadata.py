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

    run_id: ndarray[str]
    """Unique identifier of the simulation, generated when the model is run.

    It is the identifier of the simulation for VIMSEO, and not the one of a database
    like MLflow. A result retrieved from the cache keeps the identifier of the
    simulation that created it."""

    analysis_node_run_id: ndarray[str]
    """Unique identifier of the analysis node run during which the simulation was executed.

    Empty if the model was not executed by an analysis node."""

    study_name: ndarray[str]
    """The study in which the simulation is archived."""

    status: ndarray[str]
    """The status of the simulation: ``RUNNING``, ``FINISHED`` or ``FAILED``.

    The outputs of a model always hold ``FINISHED``; the archive writes ``RUNNING``
    when the job starts and ``FAILED`` when it raises."""


MetaDataNames = StrEnum("MetaDataNames", [field.name for field in fields(MetaData)])


# Deliberately aberrant values: they only give the types of the metadata to the
# output grammar of the models, and must never be found in the outputs of a model.
DEFAULT_METADATA = {
    name.value: value
    for name, value in {
        MetaDataNames.model: array(["__default_model__"]),
        MetaDataNames.load_case: array(["__default_load_case__"]),
        MetaDataNames.error_code: array([-666]),
        MetaDataNames.description: array(["__default_description__"]),
        MetaDataNames.job_name: array(["__default_job_name__"]),
        MetaDataNames.persistent_result_files: array(["__default_file__"]),
        MetaDataNames.n_cpus: array([-1]),
        MetaDataNames.date: array(["1900-01-01 00:00:00"]),
        MetaDataNames.cpu_time: array([-1.0]),
        MetaDataNames.user: array(["__default_user__"]),
        MetaDataNames.machine: array(["__default_machine__"]),
        MetaDataNames.vims_git_version: array(["__default_git_version__"]),
        MetaDataNames.directory_archive_root: array(["__default_archive_root__"]),
        MetaDataNames.directory_archive_job: array(["__default_archive_job__"]),
        MetaDataNames.directory_scratch_root: array(["__default_scratch_root__"]),
        MetaDataNames.directory_scratch_job: array(["__default_scratch_job__"]),
        MetaDataNames.run_id: array(["__default_run_id__"]),
        MetaDataNames.analysis_node_run_id: array(["__default_analysis_node_run_id__"]),
        MetaDataNames.study_name: array(["__default_study__"]),
        MetaDataNames.status: array(["__default_status__"]),
    }.items()
}
