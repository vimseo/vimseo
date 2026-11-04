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

from dataclasses import dataclass

import pytest

import vimseo.problems.load_cases.mock as _mock_mod
from vimseo.core.load import Load
from vimseo.core.load import LoadDirectionLiteral
from vimseo.core.load import LoadSign
from vimseo.core.load import LoadType
from vimseo.core.load_case import LoadCase
from vimseo.core.load_case_factory import LoadCaseFactory

_LC1_JSON = _mock_mod.__file__.replace("mock.py", "LC1.json")


def test_load_case():
    """Check that a load case is correctly instantiated."""
    lc = LoadCaseFactory().create("LC2")
    assert lc.name == "LC2"
    assert lc.summary == "A second mock load case."
    assert lc.PLOTS == [("y1", "y1_2")]
    assert lc.image_path is None


def test_load_case_with_domain():
    """Check that a load case with a domain is correctly instantiated."""
    lc = LoadCaseFactory().create("LC1", domain="Metallic")
    assert lc.domain == "Metallic"
    assert lc.name == "LC1"


def test_load_case_description():
    """The rendering is compact and does not include the plots."""
    lc = LoadCaseFactory().create("Beam_Cantilever")

    default_text = str(lc)
    assert default_text.startswith("Load case Beam_Cantilever:")
    assert (
        "Boundary condition variables: imposed_displacement, relative_load_location"
        in default_text
    )
    assert "Plots:" not in default_text
    assert "[" not in default_text  # no Python list repr


def test_load_case_description_includes_domain_when_set():
    """The domain line only appears in the description when a domain is set."""
    lc = LoadCase(name="Test")
    assert "Domain:" not in str(lc)

    lc_with_domain = LoadCase(name="Test", domain="Metallic")
    assert "Domain: Metallic" in str(lc_with_domain)


def test_load_case_description_includes_load_when_set():
    """The load block only appears in the description when the load is non-empty."""

    @dataclass
    class _LoadedCase(LoadCase):
        def get_load(self) -> Load:
            return Load(
                direction=LoadDirectionLiteral.LL,
                sign=LoadSign.POSITIVE,
                type=LoadType.STRESS,
            )

    lc = _LoadedCase(name="Test")
    text = str(lc)
    assert "Load:" in text
    assert "direction = LL" in text
    assert "sign = positive" in text
    assert "type = stress" in text


def test_stray_json_rejected():
    """A stray JSON file next to a load case class raises ValueError mentioning PLOTS."""
    from pathlib import Path

    stray = Path(_LC1_JSON)
    stray.write_text('{"plot_parameters": {"plots": []}}')
    try:
        with pytest.raises(ValueError, match="PLOTS"):
            LoadCaseFactory().create("LC1")
    finally:
        stray.unlink()
