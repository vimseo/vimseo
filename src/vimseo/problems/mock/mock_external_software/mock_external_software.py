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

from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import atleast_1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.job_executor.job_executor_factory import JobExecutorFactory
from vimseo.utilities.test_utils import get_working_mock_command

if TYPE_CHECKING:
    from vimseo.core.load_case import LoadCase


class MockExternalSoftware_LC1(ExternalSoftwareComponent):
    """Standalone component for MockModelPersistent."""

    USE_JOB_DIRECTORY = True

    auto_detect_grammar_files = False

    def __init__(self, load_case: LoadCase | None = None):
        super().__init__(load_case=load_case)
        default_inputs = {
            "x1": atleast_1d(2.0),
        }
        self.input_grammar.update_from_data(default_inputs)
        self.output_grammar.update_from_data({
            "y1": atleast_1d(0.0),
        })
        self.default_input_data.update(default_inputs)

        self.set_job_executor(
            JobExecutorFactory().create(
                "BaseInteractiveExecutor",
                get_working_mock_command(),
            )
        )

    def post_run(self, input_data, output_data):
        output_data["y1"] = input_data["x1"]


class MockExternalSoftware(IntegratedModel):
    """Mock model with a dummy external software component."""

    def __init__(self, load_case_name: str, **options):
        options = IntegratedModelSettings(**options).model_dump()
        compo = ComponentFactory().create(
            "MockExternalSoftware",
            load_case=LoadCaseFactory().create(load_case_name),
        )
        if compo is None:
            msg = "Failed component factory "
            raise ValueError(msg, load_case_name)
        super().__init__(
            load_case_name,
            [compo],
            **options,
        )
