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

from typing import TYPE_CHECKING

from numpy import array
from numpy import atleast_1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.components.post.post_processor import PostProcessor
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings

if TYPE_CHECKING:
    from vimseo.core.load_case import LoadCase

RESULT_FILE_NAME = "result.txt"


class MockFaultyRunPost_LC1(PostProcessor):
    """A standalone PostProcessor exercising ``POSTPROCESS_DESPITE_FAULTY_RUN``.

    Mimics a solver-specific postprocessor (e.g. Abaqus) that overrides
    :meth:`_can_postprocess` to look for a result file in the job directory, and
    whose ``_run`` follows the pattern described on
    :attr:`.PostProcessor.POSTPROCESS_DESPITE_FAULTY_RUN`: fall back to NaN
    outputs immediately if the run failed and opt-in is off, otherwise only fall
    back if the job directory turns out not to be usable.
    """

    USE_JOB_DIRECTORY = True

    auto_detect_grammar_files = False

    def __init__(self, load_case: LoadCase | None = None):
        super().__init__(load_case=load_case)
        default_inputs = {
            "x1": atleast_1d(2.0),
            "run_succeeds": atleast_1d(True),
            "result_file_written": atleast_1d(True),
        }
        self.input_grammar.update_from_data(default_inputs)
        self.output_grammar.update_from_data({
            "y1": atleast_1d(0.0),
            "y2": atleast_1d(0.0),
        })
        self.default_input_data.update(default_inputs)

    def _can_postprocess(self) -> bool:
        return (self.job_directory / RESULT_FILE_NAME).exists()

    def _run(self, input_data):
        run_succeeds = bool(input_data["run_succeeds"][0])
        if bool(input_data["result_file_written"][0]):
            (self.job_directory / RESULT_FILE_NAME).write_text(str(input_data["x1"][0]))

        if not run_succeeds:
            if not self.POSTPROCESS_DESPITE_FAULTY_RUN or not self._can_postprocess():
                return self._generate_failed_output_data()

            # Partial recovery: y1 can still be derived from the result file,
            # but y2 needs data that the faulty run never produced.
            return self._generate_nan_outputs(
                existing_data={
                    "y1": input_data["x1"] * 2,
                    MetaDataNames.error_code: array([0]),
                }
            )

        return {
            "y1": input_data["x1"] * 2,
            "y2": input_data["x1"] * 3,
            MetaDataNames.error_code: array([0]),
        }


class MockFaultyRunPost(IntegratedModel):
    """Mock model with a standalone :class:`.MockFaultyRunPost_LC1` component."""

    def __init__(self, load_case_name: str, **options):
        options = IntegratedModelSettings(**options).model_dump()
        compo = ComponentFactory().create(
            "MockFaultyRunPost",
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
