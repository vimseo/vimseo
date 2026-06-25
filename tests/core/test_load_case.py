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

from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.tools.post_tools.plot_parameters import PlotParameters


def test_load_case():
    """Check that a load case is correctly instantiated."""
    lc = LoadCaseFactory().create("LC2")
    assert lc.name == "LC2"
    assert lc.summary == "A second mock load case."
    assert isinstance(lc.plot_parameters, PlotParameters)
    assert lc.plot_parameters.curves == [("y1", "y1_2")]
    assert lc.image_path is None


def test_load_case_with_domain():
    """Check that a load case with a domain is correctly instantiated."""
    lc = LoadCaseFactory().create("LC1", domain="Metallic")
    assert lc.domain == "Metallic"
    assert lc.name == "LC1"
