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

from shutil import copy
from typing import TYPE_CHECKING
from typing import ClassVar

from numpy import atleast_1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.problems.mock.mock_fields.fields import MOCK_FIELDS_DIR

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from pathlib import Path

    from vimseo.core.load_case import LoadCase


class MockComponentField_LC1(BaseComponent):
    """Standalone component for MockModelField."""

    USE_JOB_DIRECTORY = True
    auto_detect_grammar_files = False

    FILES_TO_COPY: ClassVar[Sequence[Path | str]] = ["Pyramid.vtk"]

    def __init__(self, load_case: LoadCase):
        super().__init__(load_case)
        self.__default_inputs = {
            "x1": atleast_1d(2.0),
        }
        self.input_grammar.update_from_data(self.__default_inputs)
        self.output_grammar.update_from_data({
            "y1": atleast_1d(0.0),
            "error_code": atleast_1d(0),
        })
        self.default_input_data.update(self.__default_inputs)

    def _run(self, input_data):
        for file_name in self.FILES_TO_COPY:
            copy(MOCK_FIELDS_DIR / file_name, self.job_directory)
        return {"y1": input_data["x1"], "error_code": atleast_1d([0])}


class MockModelFields(IntegratedModel):
    """Mock model handling Field files."""

    FIELDS_FROM_FILE: ClassVar[Mapping[str, str]] = {"pyramid": r"^Pyramid\.vtk$"}

    def __init__(self, load_case_name: str, **options):
        options = IntegratedModelSettings(**options).model_dump()
        super().__init__(
            load_case_name,
            [
                ComponentFactory().create(
                    "MockComponentField",
                    load_case=LoadCaseFactory().create(load_case_name),
                )
            ],
            **options,
        )
