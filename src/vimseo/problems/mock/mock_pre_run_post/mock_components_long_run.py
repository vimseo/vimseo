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
import sys
from typing import TYPE_CHECKING

from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.job_executor.base_executor import JobExecutor

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.material.material import Material

LOGGER = logging.getLogger(__name__)


class MockLongRun(ExternalSoftwareComponent):
    """A mock class for emulation of a long run.

    Simulation time is equal to ``input_data|"x_1"]`` seconds."""

    def __init__(
        self,
        load_case_name: str = "",
        material_grammar_file: Path | str = "",
        material: Material | None = None,
        check_subprocess: bool = False,
    ) -> None:
        super().__init__(
            load_case_name, material_grammar_file, material, check_subprocess
        )
        self._job_executor = JobExecutor("")

    def _run(self, input_data):

        simulation_time = int(input_data["x2"][0])
        LOGGER.info(f"Executing a mock run of {simulation_time} seconds.")
        if sys.platform.startswith("win"):
            self._job_executor.execute(
                f"powershell Start-Sleep -Seconds {simulation_time}"
            )
        else:
            self._job_executor.execute(f"sleep {simulation_time}")

        x2 = input_data["x2"]
        y0 = x2 * 2
        return {"y0": y0}
