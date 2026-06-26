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

from pydantic import ConfigDict
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.storage_management.archive_settings import BaseArchiveSettings
from vimseo.storage_management.scratch_settings import DirectoryScratchSettings


class IntegratedModelSettings(BaseArchiveSettings, DirectoryScratchSettings):
    """The options of the ``IntegratedModel`` constructor."""

    model_config = ConfigDict(extra="forbid")

    check_subprocess: bool = Field(
        default=False,
        description="Whether to raise an error if a subprocess of a model component "
        "fails",
    )

    cache_file_path: str | Path = ""

    archive_manager: str = config.archive_manager
