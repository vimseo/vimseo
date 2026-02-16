# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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

"""Global VIMSEO configuration."""

from __future__ import annotations

import logging

from pydantic import Field

from vimseo.config.base_configuration import BaseConfiguration
from vimseo.config.config_components import DatabaseConfiguration
from vimseo.config.config_components import Solver

LOGGER = logging.getLogger(__name__)


ENV_PREFIX = "VIMSEO_"


class VimseoSettings(
    BaseConfiguration,
    validate_assignment=True,
    env_nested_delimiter="__",
    env_prefix=ENV_PREFIX,
    env_file=".env",
    # nested_model_default_partial_update=True,
):  # noqa: N801
    """Global configuration."""

    logging: str = Field(default="info")

    solvers: dict[str, Solver] = Field(
        default={"dummy": Solver()}, description="The solver command."
    )

    root_directory: str = Field(
        default="", description="The root directory where tool results are written."
    )

    working_directory: str = Field(
        default="",
        description="The working directory where "
        "tool results are written. If left to empty string, results are exported in "
        "unique directories created under the root directory. If a path is prescribed, "
        "results are exported under this path.",
    )

    archive_manager: str = Field(
        default="DirectoryArchive", description="The archive manager"
    )

    database: DatabaseConfiguration = Field(
        default=DatabaseConfiguration(), description=""
    )
