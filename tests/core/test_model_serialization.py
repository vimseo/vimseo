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

import pickle
from pathlib import Path

import pytest
from numpy.testing import assert_array_equal

from vimseo.api import create_model


@pytest.mark.skip(reason="Serialization not maintained")
@pytest.mark.parametrize(
    ("model_name", "load_case"),
    [
        pytest.param("MockModelWithMaterial", "LC1"),
        pytest.param("BendingTestAnalytical", "Cantilever"),
    ],
)
def test_model_serialization(tmp_wd, model_name, load_case):
    """Check that models can be serialized."""
    model = create_model(model_name, load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    file_path = f"{model.__class__.__name__}.pickle"
    reference_output_data = model.execute()

    with Path(file_path).open("wb") as f:
        pickle.dump(model, f)

    with Path(file_path).open("rb") as f:
        pickled_model = pickle.load(f)

    output_data = pickled_model.execute()

    for name in reference_output_data:
        assert_array_equal(reference_output_data[name], output_data[name])
