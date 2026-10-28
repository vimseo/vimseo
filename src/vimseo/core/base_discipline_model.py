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

from numpy import atleast_1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.discipline_wrapper_component import (
    DisciplineWrapperComponent,
)
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.utilities.json_grammar_utils import check_grammar_restriction
from vimseo.utilities.json_grammar_utils import to_json_grammar

if TYPE_CHECKING:
    from pathlib import Path

    from gemseo.core.discipline import Discipline

    from vimseo.material.material import Material


class BaseDisciplineModel(IntegratedModel):
    """A model wrapping a single GEMSEO :class:`~gemseo.core.discipline.Discipline`.

    The wrapped discipline is provided through the ``_DISCIPLINE`` class attribute.

    The values of the material, declared by ``MATERIAL_FILE`` or passed to the
    constructor, are the default values of the discipline inputs of the same names.

    The inputs can be bounded by a JSON grammar file, declared by
    ``_INPUT_GRAMMAR_FILE``.
    """

    _DISCIPLINE: ClassVar[Discipline | None] = None
    _EXPECTED_LOAD_CASE: ClassVar[str] = ""

    _INPUT_GRAMMAR_FILE: ClassVar[Path | str] = ""
    """The path to a JSON grammar file restricting the input grammar of the discipline.

    Its properties replace those of the same names in the input grammar of the
    discipline, e.g. to bound some inputs (``minimum`` and ``maximum`` of ``items``).
    It can only restrict this grammar: a variable unknown to the discipline, a
    different type or a looser bound raises a ``ValueError``. The file can be written
    from the discipline by the command ``vimseo_wrap write-grammar``.
    """

    def __init__(
        self,
        load_case_name: str = "Dummy",
        material: str | Path | Material | None = None,
        **options,
    ):
        """Build the model from a copy of the class discipline.

        Args:
            material: The material, overriding ``MATERIAL_FILE``: a material name,
                the path to a material JSON file, or a :class:`.Material`.

        Raises:
            ValueError: When a property of the material is not an input of the
                discipline.
        """
        options = IntegratedModelSettings(**options).model_dump()
        if load_case_name != self._EXPECTED_LOAD_CASE:
            msg = f"The load case should be {self._EXPECTED_LOAD_CASE}."
            raise ImportError(msg)
        material = self._load_material(material)
        discipline = deepcopy(self._DISCIPLINE)
        # The model manages the cache: a cache left on the wrapped discipline would
        # answer even when the model cache is disabled, and the model would then
        # archive a simulation that the discipline did not run.
        discipline.cache = None
        if material is not None:
            values = material.get_values_as_dict()
            unknown_names = sorted(values.keys() - set(discipline.input_grammar.names))
            if unknown_names:
                msg = (
                    f"The properties {unknown_names} of the material {material.name} "
                    f"are not inputs of the discipline {discipline.name}."
                )
                raise ValueError(msg)
            discipline.default_input_data.update({
                name: atleast_1d(value) for name, value in values.items()
            })
        super().__init__(
            load_case_name,
            [DisciplineWrapperComponent(load_case_name, discipline)],
            material=material,
            **options,
        )

    def _update_input_grammar(self) -> None:
        """Restrict the input grammar with ``_INPUT_GRAMMAR_FILE``.

        The input grammar becomes a JSON grammar, built from the discipline one, which
        keeps the default values and the required names of the model.

        Raises:
            ValueError: When the file does more than restrict the input grammar of the
                discipline.
        """
        if self._INPUT_GRAMMAR_FILE == "":
            return
        discipline_grammar = to_json_grammar(self.run._discipline.input_grammar)
        check_grammar_restriction(discipline_grammar, self._INPUT_GRAMMAR_FILE)
        grammar = to_json_grammar(discipline_grammar, f"{self.name}_input")
        # A property of the file replaces the property of the same name.
        grammar.update_from_file(self._INPUT_GRAMMAR_FILE)
        old_grammar = self.input_grammar
        for name in old_grammar.names:
            grammar.required_names.add(name)
        grammar.defaults.update(old_grammar.defaults)
        self.input_grammar = grammar
