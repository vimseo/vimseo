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

import re
from math import inf
from pathlib import Path

import numpy as np
import pytest
from gemseo.core.grammars.errors import InvalidDataError
from numpy import array
from numpy import atleast_1d
from numpy.testing import assert_allclose
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import DEFAULT_METADATA
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.pre_run_post_model import PreRunPostModel
from vimseo.job_executor.base_user_job_options import BaseUserJobSettings
from vimseo.problems.mock.mock_pre_run_post.mock_with_material import (
    MockModelWithMaterial,
)
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc1_overall_function,
)
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc2_overall_function,
)

JOB_NAME = "DummyJobDir"


def test_check_data_flow(tmp_wd):
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    expected = {
        "model_inputs": [
            "x1_maximum_only",
            "x1",
            "x1_minimum_only",
            "x1_no_bounds",
        ],
        "model_outputs": ["y1", *model.get_metadata_names()],
        "MockPre_LC1": {
            "inputs": [
                "x1_maximum_only",
                "x1",
                "x1_minimum_only",
                "x1_no_bounds",
            ],
            "outputs": ["x2"],
        },
        "MockRun": {
            "inputs": [
                "x2",
                "x1_maximum_only",
                "x1",
                "x1_minimum_only",
                "x1_no_bounds",
            ],
            "outputs": ["y0"],
        },
        "MockPost_LC1": {
            "inputs": ["y0"],
            "outputs": [MetaDataNames.error_code.name, "y1"],
        },
    }

    for io_key in ["model_inputs", "model_outputs"]:
        assert set(expected[io_key]) == set(model.get_dataflow()[io_key])
    for component_name in ["MockPre_LC1", "MockRun", "MockPost_LC1"]:
        for io_key in ["inputs", "outputs"]:
            assert set(expected[component_name][io_key]) == set(
                model.get_dataflow()[component_name][io_key]
            )


@pytest.mark.parametrize("load_case", ["LC1", "LC2"])
def test_execute(tmp_wd, load_case):
    """Check that after model execution, the output value is coherent regarding the
    default inputs."""
    model = create_model("MockModel", load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    out = model.execute()
    assert (
        model.default_input_data["x1"] == model._pre_processor.default_input_data["x1"]
    )
    assert out["y1"] == array([
        mock_model_lc1_overall_function(model.default_input_data["x1"])
    ])
    if load_case == "LC2":
        assert out["y1_2"] == array([
            mock_model_lc2_overall_function(
                model.default_input_data["x1"], model.default_input_data["x1_2"]
            )[1]
        ])


def test_metadata_added_to_outputs(tmp_wd):
    """Check that metadata variables are added as output data of the model."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    out = model.get_output_data_names()
    assert set(out) == {"y1", *list(DEFAULT_METADATA.keys())}


def test_metadata_vars_from_outputs(tmp_wd):
    """Check that metadata are removed when asked so."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    out = model.get_output_data_names(remove_metadata=True)
    assert set(out) == {
        "y1",
    }


@pytest.mark.parametrize(
    ("var_name", "value", "error_msg"),
    [
        (
            "x1",
            1.6,
            (
                "Grammar MockPre_LC1_discipline_input: validation failed.\n"
                "error: data.x1[0] must be smaller than or equal to 1.5"
            ),
        ),
        (
            "x1",
            -1.1,
            (
                "Grammar MockPre_LC1_discipline_input: validation failed.\n"
                "error: data.x1[0] must be bigger than or equal to -1.0"
            ),
        ),
    ],
)
def test_bounds_checking(tmp_wd, var_name, value, error_msg):
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    var_name = "x1"
    with pytest.raises(InvalidDataError) as exc_info:
        model.execute({var_name: array([value])})
    assert str(exc_info.value) == error_msg


def test_no_bounds_definition(tmp_wd):
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    assert model.lower_bounds == {"x1": -1.0, "x1_minimum_only": -3.0}
    assert model.upper_bounds == {"x1": 1.5, "x1_maximum_only": 2.0}
    assert model.input_space == {
        "x1": [-1.0, 1.5],
        "x1_maximum_only": [-inf, 2.0],
        "x1_minimum_only": [-3.0, inf],
        "x1_no_bounds": [-inf, inf],
    }


def test_with_material_file(tmp_wd):
    """Check that for a model with a material file, material properties can be passed as
    inputs and be available as input for the pre and run components."""
    e1_value = atleast_1d(1.4e5)
    m = MockModelWithMaterial("LC1")
    m.execute({"E1": e1_value})
    assert_allclose(m.get_input_data()["E1"], e1_value)
    assert_allclose(m._chain.get_input_data()["E1"], e1_value)
    assert_allclose(m._pre_processor.get_input_data()["E1"], e1_value)
    assert_allclose(m.run.get_input_data()["E1"], e1_value)


def test_metadata(tmp_wd):
    """Test that internal data (used for metadata) are in the output grammar with correct
    values."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    for k in model.get_metadata_names():
        assert k in model.output_grammar.names
    model.execute()
    output_data = model.get_output_data()

    for k in MetaDataNames:
        assert k in output_data, k

    assert output_data[MetaDataNames.model][0] == "MockModel"
    assert output_data[MetaDataNames.load_case][0] == "LC1"
    assert output_data[MetaDataNames.error_code][0] == 0
    assert output_data[MetaDataNames.description][0] == ""
    assert output_data[MetaDataNames.job_name][0] == ""
    assert len(output_data[MetaDataNames.persistent_result_files]) == 1
    assert output_data[MetaDataNames.n_cpus][0] == 1
    assert isinstance(output_data[MetaDataNames.date][0], np.str_)

    assert output_data[MetaDataNames.cpu_time][0] >= 0.0
    assert isinstance(output_data[MetaDataNames.user][0], np.str_)
    assert isinstance(output_data[MetaDataNames.machine][0], np.str_)
    assert isinstance(output_data[MetaDataNames.vims_git_version][0], np.str_)
    assert isinstance(output_data[MetaDataNames.directory_archive_root][0], np.str_)
    assert Path(output_data[MetaDataNames.directory_archive_job][0]) == Path(
        "default_archive/MockModel/LC1/1"
    )
    assert isinstance(output_data[MetaDataNames.directory_scratch_root][0], np.str_)
    assert output_data[MetaDataNames.directory_scratch_job][0] == ""


def test_set_subprocess_checking(tmp_wd):
    """Check that the subprocess checking is modified in all model components."""
    model = create_model("MockModel", "LC1", check_subprocess=True)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    for c in model._chain.disciplines:
        assert c._check_subprocess


def test_model_description(tmp_wd):
    """Check model description."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    description = model.description
    assert description.name == model.name
    assert id(description.load_case) == id(model.load_case)
    assert description.summary == model.SUMMARY
    assert description.curves == model.CURVES

    for component_name in [
        "model_inputs",
        "model_outputs",
        model._pre_processor.name,
        model.run.name,
        model._post_processor.name,
    ]:
        assert component_name in description.dataflow

    assert set(description.default_inputs.keys()) == {
        group_name.value for group_name in PreRunPostModel.InputGroupNames
    }
    assert isinstance(
        description.default_inputs[PreRunPostModel.InputGroupNames.GEOMETRICAL_VARS][
            "height"
        ],
        list,
    )


def test_input_names_groups():
    """Check that the input variable names are split by geometrical, boundary conditions,
    material and numerical parameters."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    assert not set(model.numerical_variable_names)
    assert set(model.material_variable_names) == {"young_modulus", "nu_p"}
    assert set(model.boundary_condition_variable_names) == {
        "imposed_dplt",
        "relative_dplt_location",
    }
    assert set(model.geometrical_variable_names) == {"length", "width", "height"}


@pytest.mark.parametrize(
    ("model_name", "load_case", "user_job_options"),
    [
        ("MockModel", "LC1", BaseUserJobSettings(n_cpus=4)),
    ],
)
def test_set_job_options(tmp_wd, model_name, load_case, user_job_options):
    """Check that the job options can be modified and correctly set into account."""
    model = create_model(model_name, load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    assert model.run.n_cpus == 1
    model.run.job_executor.set_options(user_job_options)
    assert model.run.job_executor.options["n_cpus"] == 4
    assert model.run.n_cpus == 4
    model.execute()
    if model.run.job_executor._job_options:
        assert model.run.job_executor._job_options.n_cpus == 4


def test_set_bounds(tmp_wd):
    """Check that model bounds are set from material bounds."""
    model = create_model("MockModelWithMaterial", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    assert (
        model.lower_bounds["E1"]
        == model.material.material_relations[0].properties[0].lower_bound
    )
    assert (
        model.upper_bounds["E1"]
        == model.material.material_relations[0].properties[0].upper_bound
    )


def test_grammar_nb_items(tmp_wd):
    """Check that the number of items is taken into account."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    msg = "data.x1 must contain less than or equal to 1 items"
    with pytest.raises(InvalidDataError, match=re.escape(msg)):
        model.execute({"x1": array([0.5, 0.5])})


def test_with_namespace_on_input(tmp_wd):
    """Check that an ``PreRunPostModel`` with namespaces return the same results as
    without namespaces."""

    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    reference_model = create_model(
        "MockModel", "LC1", cache_file_path="reference_model_cache.hdf"
    )
    model.add_namespace_to_input("x1", "pre")

    x1 = 1.05 * reference_model.default_input_data["x1"]
    data_reference = reference_model.execute({"x1": x1})
    data = model.execute({"pre:x1": x1})
    assert_array_equal(data_reference["y1"], data["y1"])
    model.EXTRA_INPUT_GRAMMAR_CHECK = False


def test_input_grammar_extras(tmp_wd):
    """Check that executing a model on variables that are not in the input grammar
    raiseas an error."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    msg = (
        "Input ['foo'] are not defined in the input grammar.Input grammar names are "
        "['x1', 'x1_maximum_only', 'x1_minimum_only', 'x1_no_bounds']."
    )
    with pytest.raises(KeyError, match=re.escape(msg)):
        model.execute({"foo": atleast_1d(0.0)})
    model.EXTRA_INPUT_GRAMMAR_CHECK = False
