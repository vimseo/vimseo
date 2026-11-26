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

from vimseo.core.components.base_component import BaseComponent
from vimseo.utilities.json_grammar_utils import check_grammar_restriction
from vimseo.utilities.json_grammar_utils import read_json_grammar
from vimseo.utilities.json_grammar_utils import to_json_grammar

if TYPE_CHECKING:
    from pathlib import Path

    from gemseo.core.discipline import Discipline

    from vimseo.core.load_case import LoadCase


class DisciplineWrapperComponent(BaseComponent):
    """A component that wraps a GEMSEO discipline."""

    auto_detect_grammar_files = False

    def __init__(
        self,
        load_case: LoadCase,
        discipline: Discipline,
        input_grammar_file: Path | str = "",
    ):
        """
        Args:
            input_grammar_file: The path to a JSON grammar file bounding the inputs of
                the discipline, i.e. giving the domain of validity of the model: the
                model reads its ``lower_bounds`` and ``upper_bounds`` from this grammar,
                e.g. to build the input space of a DOE or a calibration, and an input
                out of these bounds makes the execution fail. The discipline keeps its
                own grammar and validates its inputs with it after the component, so the
                file declares all the inputs of the discipline and only restricts them.
                If empty, the component shares the input grammar of the discipline.

        Raises:
            ValueError: When the JSON grammar file is not a valid JSON schema, misses
                an input of the discipline or does more than restrict its input grammar.
        """  # ruff: ignore[undocumented-param]
        super().__init__(load_case)

        self._discipline = discipline
        if input_grammar_file == "":
            self.input_grammar = discipline.input_grammar
        else:
            grammar = read_json_grammar(input_grammar_file)
            check_grammar_restriction(
                to_json_grammar(discipline.input_grammar), grammar
            )
            for name in discipline.input_grammar.required_names:
                grammar.required_names.add(name)
            grammar.defaults.update(discipline.input_grammar.defaults)
            self.input_grammar = grammar
        self.output_grammar = deepcopy(discipline.output_grammar)
        # The error code of a wrapped model is passed on as is.
        self._declare_error_code(self.output_grammar)

    @property
    def job_executor(self):
        """The job executor of the wrapped discipline, or ``None``.

        A wrapped model runs as a single component, so — unlike an
        :class:`~vimseo.core.components.external_software_component.ExternalSoftwareComponent`
        — this component has no executor of its own. Forwarding the wrapped
        model's single :attr:`~vimseo.core.base_integrated_model.IntegratedModel.job_executor`
        keeps it visible at the composition's top level (so a single executor can
        be enforced and driven across the whole chain) without flattening the
        wrapped model into its components. ``None`` when the wrapped discipline is
        not an integrated model (a plain GEMSEO discipline has no executor).
        """
        return getattr(self._discipline, "job_executor", None)

    def _run(self, input_data):
        # The output data of the wrapped discipline, including its error code if any,
        # are returned unchanged; a failure of the wrapped discipline raises.
        return self._discipline.execute(input_data)
