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

"""Robustness of the model HDF5 cache to the types and sizes of the data."""

from __future__ import annotations

import pytest
from numpy import array
from numpy import atleast_1d

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_settings import IntegratedModelSettings

# The inputs and the expected outputs of two points differing by all their inputs,
# including the size of ``x_vector`` and thus of ``y_vector``.
_INPUT_OUTPUT_PAIRS = (
    (
        {
            "x_float": atleast_1d(1.0),
            "x_bool": atleast_1d(False),
            "x_integer": atleast_1d(1),
            "x_string": atleast_1d("BCC"),
            "x_vector": array([1.0, 2.0]),
        },
        {
            "y_float": atleast_1d(3.0),
            "y_bool": atleast_1d(True),
            "y_integer": atleast_1d(2),
            "y_string": atleast_1d("BCC-off"),
            "y_vector": array([1.0, 2.0]),
        },
    ),
    (
        {
            "x_float": atleast_1d(2.0),
            "x_bool": atleast_1d(True),
            "x_integer": atleast_1d(5),
            "x_string": atleast_1d("FCC"),
            "x_vector": array([1.0, 2.0, 3.0]),
        },
        {
            "y_float": atleast_1d(4.0),
            "y_bool": atleast_1d(False),
            "y_integer": atleast_1d(10),
            "y_string": atleast_1d("FCC-on"),
            "y_vector": array([2.0, 4.0, 6.0]),
        },
    ),
)


class _AllTypesComponent(BaseComponent):
    """A component with bool, string, integer, float and variable-size data."""

    auto_detect_grammar_files = False

    def __init__(self, load_case=None):
        super().__init__(load_case=load_case)
        default_inputs = _INPUT_OUTPUT_PAIRS[0][0]
        self.input_grammar.update_from_data(default_inputs)
        self.output_grammar.update_from_data(_INPUT_OUTPUT_PAIRS[0][1])
        self.default_input_data.update(default_inputs)

    def _run(self, input_data):
        x_float = input_data["x_float"][0]
        x_bool = bool(input_data["x_bool"][0])
        return {
            "y_float": atleast_1d(x_float * (2.0 if x_bool else 3.0)),
            "y_bool": atleast_1d(not x_bool),
            "y_integer": atleast_1d(2 * int(input_data["x_integer"][0])),
            "y_string": atleast_1d(
                f"{input_data['x_string'][0]}-{'on' if x_bool else 'off'}"
            ),
            "y_vector": x_float * input_data["x_vector"],
        }


class _AllTypesModel(IntegratedModel):
    def __init__(self, load_case_name, **options):
        options = IntegratedModelSettings(**options).model_dump()
        component = _AllTypesComponent(
            load_case=LoadCaseFactory().create(load_case_name)
        )
        super().__init__(load_case_name, [component], **options)


def _typed(data):
    """Return the ``x_*`` and ``y_*`` values of ``data``, with their dtype kind.

    The other variables, like the metadata outputs, are ignored.
    Comparing two such dictionaries checks the values, the sizes and the types at once.

    Examples:
        >>> data = {"y_bool": array([True]), "y_vector": array([1.0, 2.0])}
        >>> _typed({**data, "run_id": array(["a1"])})
        {'y_bool': ('b', [True]), 'y_vector': ('f', [1.0, 2.0])}
    """
    return {
        name: (value.dtype.kind, value.tolist())
        for name, value in data.items()
        if name.startswith(("x_", "y_"))
    }


@pytest.mark.fast
@pytest.mark.parametrize("tolerance", [0.0, 1e-10])
def test_cache_with_all_data_types(tmp_wd, tolerance):
    """Bool, string, integer, float and variable-size data do not break the HDF5 cache.

    The HDF5 cache used to fail on string inputs with a tolerance (GEMSEO issue #1603)
    and on inputs of variable size with a tolerance (GEMSEO issue #1049).
    """
    model = _AllTypesModel("LC1")
    model.cache.tolerance = tolerance
    for inputs, expected_outputs in _INPUT_OUTPUT_PAIRS:
        model.execute(inputs)
        assert _typed(model.get_output_data()) == _typed(expected_outputs)
    assert len(model.cache) == 2

    # Re-executing the points is served by the cache: no new archived run is created.
    for inputs, expected_outputs in _INPUT_OUTPUT_PAIRS:
        model.execute(inputs)
        assert _typed(model.get_output_data()) == _typed(expected_outputs)
    assert len(model.archive_manager.get_archived_results()) == 2


@pytest.mark.fast
def test_cache_from_archive_with_all_data_types(tmp_wd):
    """The cache rebuilt from the archive keeps the values, sizes and types of the data.

    ``IntegratedModel.create_cache_from_archive`` always sets a tolerance.
    """
    # Fill the archive.
    model = _AllTypesModel("LC1")
    for inputs, _ in _INPUT_OUTPUT_PAIRS:
        model.execute(inputs)

    # Rebuild the cache of a new model from this archive.
    model_bis = _AllTypesModel("LC1")
    cache = model_bis.create_cache_from_archive()
    assert len(cache) == 2

    # The entries come in archive order: match them to the points by x_string
    entries = {str(e.inputs["x_string"][0]): e for e in cache.get_all_entries()}
    for inputs, expected_outputs in _INPUT_OUTPUT_PAIRS:
        entry = entries[inputs["x_string"][0]]
        assert _typed(entry.inputs) == _typed(inputs)
        assert _typed(entry.outputs) == _typed(expected_outputs)

    # The rebuilt cache serves the re-execution: no new archived run is created.
    for inputs, expected_outputs in _INPUT_OUTPUT_PAIRS:
        model_bis.execute(inputs)
        assert _typed(model_bis.get_output_data()) == _typed(expected_outputs)
    assert len(model_bis.archive_manager.get_archived_results()) == 2


_NON_ASCII_STRING = {"x_string": atleast_1d("Matériau")}


@pytest.mark.fast
@pytest.mark.parametrize(
    ("tolerance", "first_inputs", "second_inputs"),
    [
        pytest.param(
            0.0,
            {"x_integer": atleast_1d(1)},
            {"x_integer": atleast_1d(1.0)},
            marks=pytest.mark.xfail(
                strict=True,
                reason="GEMSEO issue #1530: without tolerance, "
                "an integer value given as a float is a cache miss.",
            ),
            id="integer_as_float-no_tolerance",
        ),
        *(
            pytest.param(
                tolerance,
                _NON_ASCII_STRING,
                _NON_ASCII_STRING,
                marks=pytest.mark.xfail(
                    raises=RuntimeError,
                    strict=True,
                    reason="GEMSEO issue #2057: "
                    "the HDF5 cache cannot store a non-ASCII string.",
                ),
                id=f"non_ascii_string-{label}",
            )
            for tolerance, label in ((0.0, "no_tolerance"), (1e-10, "tolerance"))
        ),
    ],
)
def test_cache_known_limitations(tmp_wd, tolerance, first_inputs, second_inputs):
    """Known limitations of the GEMSEO HDF5 cache, expected to fail until fixed.

    Executing ``second_inputs`` after ``first_inputs`` should be served by the cache.
    """
    model = _AllTypesModel("LC1")
    model.cache.tolerance = tolerance
    model.execute(first_inputs)
    model.execute(second_inputs)
    assert len(model.archive_manager.get_archived_results()) == 1
