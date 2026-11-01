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

"""Global VIMSEO configuration."""

from __future__ import annotations

import logging

from pydantic import Field

from vimseo.config.base_configuration import BaseConfiguration
from vimseo.config.config_components import DatabaseConfiguration
from vimseo.config.config_components import Solver

LOGGER = logging.getLogger(__name__)


ENV_PREFIX = "VIMSEO_"

DEFAULT_STUDY_NAME = "default_study"
"""The default study, distinct from the MLflow experiment ``Default``."""


class VimseoSettings(
    BaseConfiguration,
    validate_assignment=True,
    env_nested_delimiter="__",
    env_prefix=ENV_PREFIX,
    env_file=".env",
    # nested_model_default_partial_update=True,
):  # ruff: ignore[invalid-class-name]
    """Global configuration."""

    logging: str = Field(default="info")

    solvers: dict[str, Solver] = Field(
        default={
            "dummy": Solver(),
            "abaqus": Solver(
                job_executor="InteractiveAbaqus",
                command_pre="abq2022 cae noGUI={{abaqus_script}}",
                command_run="abq2022 job={{job_name}} cpus={{n_cpus}}{% if subroutine_names|length > 0 %} user={{subroutine_names[0]}}{% endif %} {% if is_implicit == False %}double=both {% endif %}inter",
                command_post="",
            ),
        },
        description="The solver command.",
    )

    root_directory: str = Field(
        default="",
        description="The root directory where analysis node results are written.",
    )

    working_directory: str = Field(
        default="",
        description="The working directory where "
        "analysis_node results are written. If left to empty string, results are exported in "
        "unique directories created under the root directory. If a path is prescribed, "
        "results are exported under this path.",
    )

    run_archive_manager: str = Field(
        default="DirectoryArchive",
        description="The archive manager of the simulations.",
    )

    analysis_node_archive_manager: str | None = Field(
        default=None,
        description="The archive manager of the results of the analysis nodes. If not set, it "
        "is the ``run_archive_manager``. Set it to ``none`` to disable the archive of "
        "the analysis node results.",
    )

    study_name: str = Field(
        default=DEFAULT_STUDY_NAME,
        description="The study in which the simulations and the analysis node runs are "
        "archived.",
    )

    database: DatabaseConfiguration = Field(
        default=DatabaseConfiguration(), description=""
    )
