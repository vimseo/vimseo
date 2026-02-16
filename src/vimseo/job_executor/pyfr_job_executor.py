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

import logging
from pathlib import Path

from vimseo.job_executor.base_interactive_executor import BaseInteractiveExecutor
from vimseo.job_executor.base_user_job_options import BaseUserJobSettings

LOGGER = logging.getLogger(__name__)


class PyFRJobSettings(BaseUserJobSettings):
    """The user job options for PyFR."""

    backend: str = "cuda"


class PyFRInteractiveExecutor(BaseInteractiveExecutor):
    """An executor to execute PyFR."""

    def _fetch_convergence(self):
        files = sorted(Path(self._job_directory).glob("*.pyfrs"))
        times = [f.basename.split("-")[-1] for f in files]
        if len(times) > 0:
            LOGGER.info(f"Current time: {times[-1]}")
