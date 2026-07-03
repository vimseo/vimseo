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

from copy import deepcopy
from typing import TYPE_CHECKING

from gemseo.core.execution_status import ExecutionStatus
from numpy import atleast_1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.model_metadata import MetaDataNames

if TYPE_CHECKING:
    from gemseo.core.discipline import Discipline

    from vimseo.core.load_case import LoadCase


class DisciplineWrapperComponent(BaseComponent):
    """A component that wraps a GEMSEO discipline."""

    auto_detect_grammar_files = False

    def __init__(self, load_case: LoadCase, discipline: Discipline):
        super().__init__(load_case)

        self._discipline = discipline
        self.input_grammar = discipline.input_grammar
        self.output_grammar = deepcopy(discipline.output_grammar)
        self.output_grammar.update_from_data({
            MetaDataNames.error_code.name: atleast_1d(
                IntegratedModel._ERROR_CODE_DEFAULT
            )
        })

    def _run(self, input_data):
        output_data = self._discipline.execute(input_data)
        output_data[MetaDataNames.error_code] = atleast_1d(
            1 if self.execution_status.value == ExecutionStatus.Status.FAILED else 0
        )
        return output_data
