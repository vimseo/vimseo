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
from typing import Any
from typing import ClassVar

from gemseo import READ_ONLY_EMPTY_DICT
from gemseo.core.discipline import Discipline

if TYPE_CHECKING:
    from gemseo.core.discipline.discipline_data import DisciplineData
    from gemseo.typing import StrKeyMapping


class GemseoDisciplineWrapper(Discipline):
    EXTRA_INPUT_GRAMMAR_CHECK: ClassVar[bool] = False

    def _get_input_data(self) -> dict[str, Any]:
        return self.get_input_data(with_namespaces=False)

    def get_input_data_names(self):
        return list(self.input_grammar.names)

    def get_output_data_names(self):
        return list(self.output_grammar.names)

    def execute(
        self,
        input_data: StrKeyMapping = READ_ONLY_EMPTY_DICT,
    ) -> DisciplineData:

        if self.EXTRA_INPUT_GRAMMAR_CHECK:
            from vimseo.core.base_integrated_model import IntegratedModel

            all_input_names = list(input_data.keys()) + list(
                self.default_input_data.keys()
            )

            if (isinstance(self, (IntegratedModel))) and not set(
                all_input_names
            ).issubset(set(self.input_grammar.names)):
                extra_inputs = list(
                    set(all_input_names) - set(self.input_grammar.names)
                )
                msg = (
                    f"Input {extra_inputs} are not defined in the input grammar."
                    f"Input grammar names are {list(self.input_grammar.names)}."
                )
                raise KeyError(msg)

        return super().execute(input_data)
