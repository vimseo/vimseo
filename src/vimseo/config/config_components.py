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

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from vimseo.job_executor.job_executor_factory import JobExecutorFactory

LOGGER = logging.getLogger(__name__)


ENV_PREFIX = "VIMSEO_"


class DatabaseConfiguration(BaseModel):
    mode: str = Field(default="Local")
    local_uri: str = Field(
        default="",
    )
    team_uri: str = Field(default="https://mlflow.irt-aese.local/")
    username: str = Field(default="")
    password: str = Field(default="")
    experiment_name: str = Field(default="")
    use_insecure_tls: bool = Field(default=False)
    ssl_certificate_file: str = Field(default="")


class Solver(BaseModel):
    job_executor: str | None = Field(
        default=None, description="The job executor to use."
    )
    command_run: str = Field(default="")
    command_pre: str = Field(default="")
    command_post: str = Field(default="")

    @field_validator("job_executor")
    @classmethod
    def __validate_job_executor(cls, v: str | None) -> str | None:
        if v and v not in JobExecutorFactory().class_names:
            msg = (
                f"{v} does not exist. Available job executors "
                f"{JobExecutorFactory().class_names}."
            )
            raise ValueError(msg)
        return v
