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

# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.core.grammars.pydantic_grammar import PydanticGrammar
from numpy import linspace

from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.job_executor.base_executor import BaseJobExecutor
from vimseo.job_executor.job_executor_factory import JobExecutorFactory
from vimseo.problems.cfd.couette_2d import COUETTE_2D_DIR
from vimseo.problems.cfd.couette_2d.pre_couette_2d import PreCouette2DInputGrammar
from vimseo.utilities.file_utils import wait_for_file

if TYPE_CHECKING:
    from collections.abc import Sequence

LOGGER = logging.getLogger(__name__)


class RunPyFR(ExternalSoftwareComponent):
    USE_JOB_DIRECTORY = True

    _PERSISTENT_FILE_NAMES: ClassVar[Sequence[str]] = [
        f"couette-flow-{int(t):03d}_{field}.png"
        for field in ["Velocity", "Density"]
        for t in linspace(0, 9, num=10)
    ]

    default_grammar_type = "PydanticGrammar"

    def __init__(self, **options):
        super().__init__(**options)

        # The material grammar must be added to the grammar, since we do not use
        # a JSON material grammar passed to the component
        # (through material_grammar_file arg)
        self.input_grammar.update_from_types(
            PydanticGrammar(
                "grammar", model=PreCouette2DInputGrammar
            )._get_names_to_types()
        )

        self.set_job_executor(
            JobExecutorFactory().create(
                "PyFRInteractiveExecutor",
                "pyfr run -b {{ backend }} couette-flow.pyfrm couette-flow.ini",
            )
        )

    def pre_run(self, input_data):
        subprocess.run(
            ["pyfr", "import", "couette-flow.msh", "couette-flow.pyfrm"],
            cwd=self._job_directory,
            capture_output=True,
        )

    def write_input_files(self, input_data):

        template = Path(COUETTE_2D_DIR / "couette_2d.ini.j2").read_text()
        input_str = BaseJobExecutor._render_template(
            template,
            {key: value[0] for key, value in input_data.items()},
        )
        Path(self.job_directory / "couette-flow.ini").write_text(input_str)

    def _is_successful_execution(
        self,
    ) -> int:
        """Check job completion by reading the last pseudo-time."""
        result_file_path = self.job_directory / "couette-flow-010.pyfrs"
        try:
            wait_for_file(result_file_path)
        except FileNotFoundError:
            return False
        else:
            return True
