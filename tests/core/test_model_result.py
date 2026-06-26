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
from pathlib import Path

import pytest
from numpy import array
from numpy import linspace
from numpy.ma.testutils import assert_array_equal
from pandas import DataFrame
from pandas._testing import assert_frame_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_result import ModelResult
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.utilities.curves import Curve
from vimseo.utilities.plotting_utils import plot_curves


def test_from_data(tmp_wd):
    """Check that a ModelResult can be created from model data."""
    model = create_model("MockModelPersistent", "LC1")
    model.execute()
    model_data = {"inputs": model.get_input_data(), "outputs": model.get_output_data()}
    result = ModelResult.from_data(model_data)
    assert result.scalars == {
        "x1": 2.0,
        "x2": 5.0,
        "y1": 7.0,
        "y3": "mock_string",
        "y4": 6.0,
    }
    assert list(result.vectors.keys()) == ["x3", "y2", "y5"]
    assert_array_equal(result.vectors["x3"], array([1.0, 2.0, 3.0]))
    assert_array_equal(result.vectors["y2"], array([1, 2, 3, 4, 5]))
    assert_array_equal(result.vectors["y5"], array([6.0, 36.0, 216.0]))
    for name, value in result.metadata.report.items():
        if name != MetaDataNames.persistent_result_files:
            assert value == model.get_output_data()[name]
        else:
            assert (value == model.get_output_data()[name]).all()
    # TODO missing test on curves


def test_plot_curves(tmp_wd):
    """Check that a model result can plot curves."""
    xc = linspace(0, 1, 10)
    curves = [Curve({"xc": xc, "yc": alpha * xc}) for alpha in linspace(0.0, 1.0, 10)]
    result = ModelResult(
        curves=curves,
    )
    plot_curves(result.curves, show=False, save=True)
    assert Path("curves.html").exists()

    curves.append(Curve({"xd": xc, "yc": xc}))
    msg = (
        "Abscissa names are not unique: "
        "['xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xd']"
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        plot_curves(result.curves, show=False, save=True)


def test_scalars_to_dataframe():
    """Check that a model result can plot scalars."""
    result = ModelResult(scalars={"x": 1.0, "y": 2.0, "s": "foo"})
    df = DataFrame([result.get_numeric_scalars()])
    expected_df = DataFrame([{"x": 1.0, "y": 2.0}])
    assert_frame_equal(df, expected_df)


def test_str():
    """A model result has a readable string representation."""
    result = ModelResult(
        scalars={"x": 1.0},
        vectors={"v": array([1.0, 2.0])},
        curves=[Curve({"xc": array([0.0, 1.0]), "yc": array([0.0, 1.0])})],
    )
    text = str(result)
    assert "Scalars:" in text
    assert "Vectors:" in text
    assert "Curves:" in text
    assert "Fields:" in text


def test_get_curve_not_found_returns_empty():
    """Requesting an unknown curve returns an empty list."""
    result = ModelResult(
        curves=[Curve({"xc": array([0.0, 1.0]), "yc": array([0.0, 1.0])})],
    )
    assert result.get_curve(("unknown_x", "unknown_y")) == []


def test_fields(tmp_wd):
    """Check that a model can read fields contained in files."""
    model = create_model(
        "MockModelFields",
        "LC1",
        model_options=IntegratedModelSettings(
            directory_scratch_persistency=PersistencyPolicy.DELETE_NEVER
        ),
    )
    model.cache = None
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    output_data = model.execute()
    assert (
        Path(output_data[MetaDataNames.directory_archive_job][0])
        / output_data["pyramid"][0]
    ).exists()

    model_data = {"inputs": model.get_input_data(), "outputs": model.get_output_data()}
    result = ModelResult.from_data(model_data, load_fields=True)
    field = result.fields["pyramid"][0]
    assert_array_equal(
        array(field.mesh_points),
        ([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]),
    )
