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

from os import environ

import pytest
from pydantic import ValidationError

from vimseo.config.global_configuration import VimseoSettings
from vimseo.config.global_configuration import _configuration as config


def test_config_from_env_var():
    """Check that configuration can be set from environment variables."""
    job_executor = config.solvers["dummy"].job_executor
    assert not job_executor
    environ["VIMSEO_SOLVERS__DUMMY__JOB_EXECUTOR"] = "BaseInteractiveExecutor"
    config_ = VimseoSettings()
    assert (
        config_.model_dump()["solvers"]["dummy"]["job_executor"]
        == "BaseInteractiveExecutor"
    )


def test_config_set_attr():
    """Check that configuration can be set from attribute assignment."""
    job_executor = config.solvers["dummy"].job_executor
    assert not job_executor
    config.solvers["dummy"].job_executor = "BaseInteractiveExecutor"
    assert (
        config.model_dump()["solvers"]["dummy"]["job_executor"]
        == "BaseInteractiveExecutor"
    )


def test_config_with_config_file(tmp_wd):
    """Check that configuration can be set from a .env file."""
    with (tmp_wd / ".env").open("w") as f:
        f.write(
            'VIMSEO_SOLVERS__DUMMY2__JOB_EXECUTOR="BaseInteractiveExecutor"\nVIMSEO_SOLVERS__DUMMY__COMMAND=""\nVIMSEO_DATABASE__MODE="Team"\n'
        )

    config = VimseoSettings()
    assert {"dummy", "dummy2"} == set(config.solvers.keys())
    assert config.database.mode == "Team"
    assert config.solvers["dummy2"].job_executor == "BaseInteractiveExecutor"


def test_config_bad_job_executor(tmp_wd):
    """Check that configuration raises error for bad job executor."""
    with (tmp_wd / ".env").open("w") as f:
        f.write('VIMSEO_SOLVERS__DUMMY2__JOB_EXECUTOR="BadExecutor"\n')

    with pytest.raises(ValidationError) as excinfo:
        VimseoSettings()
    assert "Value error, BadExecutor does not exist." in str(excinfo.value)
