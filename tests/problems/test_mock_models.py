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

import json

import pytest
from numpy import array
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.api import get_available_load_cases
from vimseo.problems.mock.output_data import MOCK_OUTPUT_DATA_DIR


@pytest.mark.parametrize(
    ("model_name", "load_case"),
    [
        pytest.param(
            str(model_name),
            str(load_case),
        )
        for model_name in [
            "MockModelPersistent",
            "MockModel",
            "MockModelWithMaterial",
        ]
        for load_case in get_available_load_cases(model_name)
    ],
)
def test_mock_models(tmp_wd, model_name, load_case):
    """Check that an Abaqus model with subroutines can be executed remotely."""

    m = create_model(
        model_name,
        load_case,
        check_subprocess=True,
    )
    m.EXTRA_INPUT_GRAMMAR_CHECK = True

    m.cache = None
    output_data = m.execute()

    # Only to regenerate reference output data
    # with open(MOCK_OUTPUT_DATA_DIR / f"{model_name}_{load_case}.json", "w") as f:
    #     json.dump(output_data, f, indent=4, ensure_ascii=True, cls=EnhancedJSONEncoder)

    expected_output_data = json.loads(
        (MOCK_OUTPUT_DATA_DIR / f"{model_name}_{load_case}.json").read_text()
    )
    tested_names = m.get_output_data_names(remove_metadata=True)
    for name in tested_names:
        assert_array_equal(array(expected_output_data[name]), output_data[name])
