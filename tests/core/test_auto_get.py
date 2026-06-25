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

import pytest

from vimseo.api import create_model


@pytest.mark.parametrize(
    ("model_name", "load_case"),
    [
        ("BendingTestAnalytical", "Cantilever"),
    ],
)
def test_auto_get_image(tmp_wd, model_name, load_case):
    """Check that the path to the image associated with a model and a load case is
    correct."""
    model = create_model(model_name, load_case)
    assert model.image_path.is_file()
    assert model.image_path.name == "Beam_Cantilever.png"
