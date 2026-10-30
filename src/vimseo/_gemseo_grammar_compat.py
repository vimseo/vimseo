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
"""Restore MRO-based JSON grammar auto-discovery.

The private gemseo fork vimseo used to depend on searched a discipline's whole
``__mro__`` for an auto-discovered JSON grammar file, not just its direct
``__bases__``. Stock gemseo only searches direct bases
(:meth:`.GrammarFactory.__search_file`), which breaks vimseo's deeper
``_IS_JSON_GRAMMAR`` discipline/analysis_node hierarchies (e.g. a grammar file defined
two or more levels up from a leaf class). Rather than restructure those
hierarchies or maintain a gemseo fork, this module patches
:class:`.GrammarFactory` in place to walk the full MRO again.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.core.grammars.factory import GrammarFactory

if TYPE_CHECKING:
    from gemseo.core.discipline import Discipline


def _search_file_via_mro(
    discipline_class: type[Discipline],
    file_name_suffix: str,
    directory_path: str | Path,
) -> Path:
    """Same as ``GrammarFactory.__search_file``, but walking the full MRO."""
    from gemseo.core.discipline.base_discipline import BaseDiscipline

    classes = [
        cls for cls in discipline_class.__mro__ if issubclass(cls, BaseDiscipline)
    ]

    for cls in classes:
        name = cls.__name__
        if not directory_path:
            class_module = sys.modules[cls.__module__]
            directory_path_ = Path(class_module.__file__).parent
        else:
            directory_path_ = Path(directory_path)
        grammar_file_path = directory_path_ / f"{name}_{file_name_suffix}.json"
        if grammar_file_path.is_file():
            return grammar_file_path

    file_name = f"{discipline_class.__name__}_{file_name_suffix}.json"
    msg = f"The grammar file {file_name} is missing."
    raise FileNotFoundError(msg)


def apply() -> None:
    """Patch :class:`.GrammarFactory` to search the full MRO."""
    # ``__search_file`` is name-mangled because it is declared private inside
    # ``GrammarFactory``; patch it under that mangled name so the (also mangled)
    # call site in ``GrammarFactory.create`` picks it up.
    GrammarFactory._GrammarFactory__search_file = staticmethod(_search_file_via_mro)
