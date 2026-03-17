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

import shutil
from typing import TYPE_CHECKING
from typing import ClassVar

import numpy as np
from numpy import array
from numpy import atleast_1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.problems.mock.mock_model_persistent import PATH_MOCK_FILES_PERSISTENT

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vimseo.core.load_case import LoadCase


class MockComponentStandalonePersistent_LC1(BaseComponent):
    """Standalone component for MockModelPersistent."""

    USE_JOB_DIRECTORY = True
    _PERSISTENT_FILE_NAMES: ClassVar[Sequence[str]] = [
        "green_ellipse.png",
        "blue_line.png",
    ]

    MOCK_FILES_NAMES: ClassVar[Sequence[str]] = [
        "original_blue_line.png",
        "original_green_ellipse.png",
    ]

    auto_detect_grammar_files = False

    def __init__(self, load_case: LoadCase | None = None):
        super().__init__(load_case=load_case)
        default_inputs = {
            "x1": atleast_1d(2.0),
            "x2": atleast_1d(5.0),
            "x3": array([1.0, 2.0, 3.0]),
        }
        self.input_grammar.update_from_data(default_inputs)
        self.output_grammar.update_from_data({
            "y1": 0.0,
            "y2": atleast_1d(0.0),
            "y3": atleast_1d("string"),
            "y4": atleast_1d(0.0),
            "y5": array([0.0, 0.0, 0.0]),
            MetaDataNames.error_code.name: array([0]),
        })
        self.default_input_data.update(default_inputs)

    def _run(self, input_data):
        x1 = input_data["x1"][0]
        x2 = input_data["x2"][0]

        y1 = x1 + x2
        y2 = np.array([1, 2, 3, 4, 5])
        y3 = np.array(["mock_string"])
        y4 = np.sum(input_data["x3"])
        y5 = array([y4, y4**2, y4**3])
        y4 = atleast_1d(y4)

        job_dir = self._job_directory

        for file_name in self.MOCK_FILES_NAMES:
            src = PATH_MOCK_FILES_PERSISTENT / file_name
            dst = job_dir / file_name.replace("original_", "")
            shutil.copy(str(src), str(dst))

        return {
            "y1": y1,
            "y2": y2,
            "y3": y3,
            "y4": y4,
            "y5": y5,
            "error_code": array([0]),
        }


class MockModelPersistent(IntegratedModel):
    """Mock model with persistent files and vectors as input and output.

    ``y5`` is a length-3 output vector, and ``x3`` is a length-3 input vector.
    """

    SUMMARY = (
        " A toy model for testing purpose of persistent data - mono-component version"
    )

    def __init__(self, load_case_name: str, **options):
        options = IntegratedModelSettings(**options).model_dump()
        compo = ComponentFactory().create(
            "MockComponentStandalonePersistent",
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
