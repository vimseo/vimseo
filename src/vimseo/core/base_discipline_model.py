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

from copy import deepcopy
from typing import TYPE_CHECKING
from typing import ClassVar

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.discipline_wrapper_component import (
    DisciplineWrapperComponent,
)
from vimseo.core.model_settings import IntegratedModelSettings

if TYPE_CHECKING:
    from gemseo.core.discipline import Discipline


class BaseDisciplineModel(IntegratedModel):
    _DISCIPLINE: ClassVar[Discipline | None] = None
    _EXPECTED_LOAD_CASE: ClassVar[str] = ""

    def __init__(self, load_case_name: str = "Dummy", **options):
        options = IntegratedModelSettings(**options).model_dump()
        if load_case_name != self._EXPECTED_LOAD_CASE:
            msg = f"The load case should be {self._EXPECTED_LOAD_CASE}."
            raise ImportError(msg)
        super().__init__(
            load_case_name,
            [DisciplineWrapperComponent(load_case_name, deepcopy(self._DISCIPLINE))],
            **options,
        )
