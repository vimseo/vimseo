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
from typing import Any
from typing import ClassVar

import numpy as np
from gemseo import READ_ONLY_EMPTY_DICT
from gemseo.core.discipline import Discipline

if TYPE_CHECKING:
    from collections.abc import Collection

    from gemseo.core.discipline.discipline_data import DisciplineData
    from gemseo.typing import StrKeyMapping


def _input_applied(applied: Any, passed: Any) -> bool:
    """Whether ``applied`` (the value the discipline used) matches ``passed``.

    Shapes are compared after ``atleast_1d`` + ``ravel`` (a scalar and its
    one-element array count as equal); numeric values with ``allclose`` (a
    tolerance loose enough that a legitimate dtype cast does not trip it),
    everything else with ``array_equal``.
    """
    a = np.atleast_1d(np.asarray(applied)).ravel()
    p = np.atleast_1d(np.asarray(passed)).ravel()
    if a.shape != p.shape:
        return False
    if np.issubdtype(a.dtype, np.number) and np.issubdtype(p.dtype, np.number):
        return bool(np.allclose(a, p, rtol=1e-6, atol=1e-12, equal_nan=True))
    return bool(np.array_equal(a, p))


def _resolve_input_name(name: str, applied_names: Collection[str]) -> str | None:
    """Map a caller-supplied key to this discipline's own grammar input name.

    ``applied_names`` is ``get_input_data(with_namespaces=True)`` taken after a
    successful ``execute()`` -- the authoritative set of inputs this discipline
    consumes, each with its namespace prefix if it has one.

    Returns ``None`` when ``name`` is not one of this discipline's inputs, e.g. a
    sibling discipline's data or this discipline's own output fed back through a
    coupled GEMSEO process.
    """
    if name in applied_names:  # genuine input (namespaced or plain)
        return name
    # Past here, ``name`` matched no declared input of this discipline.
    if ":" in name:
        # A fully-qualified ``<namespace>:<original>`` key. If this discipline
        # owned it, it would be in ``applied_names`` verbatim and matched above.
        # It did not -> the key belongs to something else in a coupled process.
        # Do not strip-and-match: ``Other:length`` would then collide with this
        # discipline's ``length`` and compare the sibling's value.
        return None
    # Bare name: may be this discipline's ``<namespace>:name`` passed without the
    # prefix. Safe to strip-match, but only if it resolves unambiguously.
    matches = [n for n in applied_names if n.rsplit(":", 1)[-1] == name]
    return matches[0] if len(matches) == 1 else None


class GemseoDisciplineWrapper(Discipline):
    """A wrapper around a Gemseo Discipline.

    It adds some practical public methods, and allows to check if extra names
    are present in the input data. It is useful to prevent users from making typos
    in the input data.
    """

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

        result = super().execute(input_data)

        # Fail loudly when an input was supplied by the caller but did not make
        # it through to the model (e.g. a dtype/shape the grammar quietly
        # rejects), which GEMSEO otherwise silently reverts to the default.
        # Scoped to the model boundary and to this discipline's *own* declared
        # inputs: in a coupled process (calibration, MDA, workflow) a sub-model
        # is handed the whole shared data dict -- sibling inputs and its own
        # fed-back outputs included -- none of which it is meant to validate.
        if input_data:
            from vimseo.core.base_integrated_model import IntegratedModel

            if isinstance(self, IntegratedModel):
                applied_data = self.get_input_data(with_namespaces=True)
                applied_names = set(applied_data)
                for name, passed in input_data.items():
                    grammar_name = _resolve_input_name(name, applied_names)
                    if grammar_name is None:
                        continue
                    applied = applied_data[grammar_name]
                    if not _input_applied(applied, passed):
                        msg = (
                            f"'{name}' was provided but not applied (dtype/shape "
                            f"mismatch?): passed {passed!r}, used {applied!r}."
                        )
                        raise ValueError(msg)

        return result
