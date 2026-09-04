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

"""The post-execute "input applied" guard in ``GemseoDisciplineWrapper``.

It fails loudly when a caller-supplied input is silently dropped instead of
applied, but must stay quiet about keys that are not this discipline's own
inputs -- sibling data and fed-back outputs handed to a sub-model inside a
coupled GEMSEO process (calibration, MDA, workflow).
"""

from __future__ import annotations

from unittest import mock

import numpy as np
import pytest

from vimseo.api import create_model
from vimseo.core.gemseo_discipline_wrapper import _input_applied
from vimseo.core.gemseo_discipline_wrapper import _resolve_input_name

_GUARD = "vimseo.core.gemseo_discipline_wrapper._input_applied"


@pytest.mark.parametrize(
    ("applied", "passed", "expected"),
    [
        (1.0, np.atleast_1d(1.0), True),  # scalar vs one-element array
        (np.array([1.0, 2.0]), np.array([1.0, 2.0]), True),
        (np.array([1.0]), np.array([1.0, 2.0]), False),  # shape mismatch
        (np.array([1]), np.array([1.0]), True),  # int/float cast
        (1.0, 1.0 + 1e-10, True),  # within tolerance
        (1.0, 1.1, False),
        (np.array(["a"]), np.array(["a"]), True),
        (np.array(["a"]), np.array(["b"]), False),
    ],
)
def test_input_applied(applied, passed, expected):
    assert _input_applied(applied, passed) is expected


@pytest.mark.parametrize(
    ("name", "applied_names", "expected"),
    [
        ("x1", {"x1", "x2"}, "x1"),  # exact, no namespace
        ("NS:x1", {"NS:x1", "NS:x2"}, "NS:x1"),  # exact, namespaced
        ("Other:x1", {"x1", "x2"}, None),  # foreign namespaced key
        ("Other:x1", {"NS:x1"}, None),  # foreign, do not strip-match
        ("x1", {"NS:x1", "NS:x2"}, "NS:x1"),  # bare name -> unique namespaced
        ("x1", {"A:x1", "B:x1"}, None),  # bare name -> ambiguous
        ("x9", {"NS:x1"}, None),  # bare name -> no match
    ],
)
def test_resolve_input_name(name, applied_names, expected):
    assert _resolve_input_name(name, applied_names) == expected


def test_guard_passes_genuine_input(tmp_wd):
    """A genuine input that is applied does not raise, and reaches the model."""
    model = create_model("MockModel", "LC1")
    out = model.execute({"x1": np.atleast_1d(1.0)})
    # MockPre: x2 = x1 + 2; MockRun/MockPost carry it through to y1.
    assert out["y1"] == np.array([7.0])


def test_guard_ignores_foreign_namespaced_key(tmp_wd):
    """A namespaced key that is not one of the model's inputs is left alone.

    This is the coupled-calibration regression: a sub-model is handed the whole
    shared data dict, including sibling inputs like ``Other:x1``.
    """
    model = create_model("MockModel", "LC1")
    out = model.execute({"x1": np.atleast_1d(1.0), "Other:x1": np.atleast_1d(999.0)})
    assert out["y1"] == np.array([7.0])


def test_guard_raises_when_input_not_applied(tmp_wd):
    """A genuine input that does not survive to the model raises ``ValueError``."""
    model = create_model("MockModel", "LC1")
    with (
        mock.patch(_GUARD, return_value=False),
        pytest.raises(ValueError, match="'x1' was provided but not applied"),
    ):
        model.execute({"x1": np.atleast_1d(1.0)})
