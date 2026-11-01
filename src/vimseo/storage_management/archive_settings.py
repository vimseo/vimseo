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

from pydantic import Field

from vimseo.analysis_nodes.base_settings import BaseSettings
from vimseo.config.global_configuration import _configuration as config
from vimseo.storage_management.base_storage_manager import PersistencyPolicy

DEFAULT_ARCHIVE_ROOT = "default_archive/"


class ArchiveLocationSettings(BaseSettings):
    """The location of an archive, shared by the models and the analysis nodes.

    A model and an analysis node configured with the same values archive their results, the
    simulations and the analysis node runs, in the same archive.
    """

    archive_manager: str | None = Field(
        default=config.run_archive_manager,
        description="The archive manager, ``DirectoryArchive`` or ``MlflowArchive``.",
    )

    directory_archive_root: Path | str = Field(
        default=(
            config.database.local_uri
            if config.database.local_uri != ""
            else DEFAULT_ARCHIVE_ROOT
        ),
        description="Path to the archive root directory, "
        "wherein unique directories will be created for each job to store "
        "persistent data."
        f"Default value is {DEFAULT_ARCHIVE_ROOT}.",
    )

    study_name: str = Field(
        default=config.study_name,
        description="The study grouping the runs in the archive: a directory "
        "{root}/{study}/ of a DirectoryArchive, an experiment of an MlflowArchive.",
    )


class BaseArchiveSettings(ArchiveLocationSettings):
    """The options of the ``IntegratedModel`` constructor."""

    archive_manager: str = Field(
        default=config.run_archive_manager,
        description="The archive manager of the simulations, ``DirectoryArchive`` or "
        "``MlflowArchive``.",
    )

    job_name: str = Field(
        default="",
        description="The name of the job, used for directory and files naming in the "
        "scratch and archive. By default, the job name is generated as a "
        "unique ID.",
    )

    directory_archive_persistency: PersistencyPolicy = Field(
        default=PersistencyPolicy.DELETE_NEVER,
        description="Whether to delete the archive job directory after "
        "post-processing.",
    )
