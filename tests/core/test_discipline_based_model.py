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

from numpy import atleast_1d

from vimseo.api import create_model


def test_discipline_based_model(tmp_wd):
    """Check that a model created from a GEMSEO discipline executes correctly."""
    model = create_model("MockCurves", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    output_data = model.execute()
    assert output_data["x"][0] == 1.0
    assert output_data["x_1"][0] == 1.0
    for name in ["y_axis", "y"]:
        assert (
            len(output_data[name])
            == model._chain.disciplines[0]._discipline.CURVE_NB_POINTS
        )


def test_discipline_isolation(tmp_wd):
    """Check that all model instances are isolated (no interference through class
    attribute ``_DISCIPLINE``."""

    model = create_model("MockCurves", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True

    model_bis = create_model("MockCurves", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model_bis.default_input_data.update({"x": atleast_1d(2.0)})

    assert model.default_input_data["x"][0] == 1.0
