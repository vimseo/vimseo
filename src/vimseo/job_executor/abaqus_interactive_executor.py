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

# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

"""An interactive job executor."""

from __future__ import annotations

import logging
import subprocess

from vimseo.job_executor.base_interactive_executor import BaseInteractiveExecutor
from vimseo.job_executor.base_user_job_options import InteractiveAbaqusUserJobSettings

LOGGER = logging.getLogger(__name__)


class InteractiveAbaqus(BaseInteractiveExecutor):
    """An interactive job executor for Abaqus."""

    DEFAULT_EXECUTABLE = "abq2022"

    _COMMAND_TEMPLATE = ""

    _IS_BLOCKING_SUBPROCESS = False

    _USER_JOB_OPTIONS_MODEL = InteractiveAbaqusUserJobSettings

    def __init__(self, command_template: str):
        super().__init__(command_template)

    def _terminate_external_software(self):
        cmd = [self._job_options.executable, f"job={self._job_name}", "terminate"]
        LOGGER.warning(f"Terminating solver with command {cmd}")
        subprocess.run(
            cmd,
            cwd=self._job_directory,
        )
