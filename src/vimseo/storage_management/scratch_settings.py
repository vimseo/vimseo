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
from pathlib import Path

from pydantic import Field

from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.tools.base_settings import BaseSettings

LOGGER = logging.getLogger(__name__)


class DirectoryScratchSettings(BaseSettings):
    """The options of the ``IntegratedModel`` constructor."""

    directory_scratch_root: Path | str = Field(
        default="default_scratch/",
        description="Path to the scratch root directory, "
        "wherein unique directories will be created to perform job "
        "executions, and possibly store the temporary scratch files."
        "Default value is './default_scratch'.",
    )

    job_name: str = Field(
        default="",
        description="The name of the job, used for directory and files naming in the "
        "scratch and archive. By default, the job name is generated as a "
        "unique ID.",
    )

    directory_scratch_persistency: PersistencyPolicy = Field(
        default=PersistencyPolicy.DELETE_IF_SUCCESSFUL,
        description="Whether to delete the scratch job directory after "
        "post-processing.",
    )
