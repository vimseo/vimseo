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
from vimseo.utilities.plotting_utils import superpose_curves


def test_from_scalars_and_vectors(tmp_wd):
    """Check that a ModelResult can be created from model data."""
    model = create_model("MockModelPersistent", "LC1")
    model.execute()
    model_data = {"inputs": model.get_input_data(), "outputs": model.get_output_data()}
    result = ModelResult.from_dict(model_data)

    assert result.scalars == {
        "x1": 2.0,
        "x2": 5.0,
        "y1": 7.0,
        "y3": "mock_string",
        "y4": 6.0,
    }

    assert list(result.vectors.keys()) == ["y2"]
    assert_array_equal(result.vectors["y2"], array([1, 2, 3, 4, 5]))

    assert result.curves[0].variable_names == ("x3", "y5")
    assert_array_equal(result.curves[0].x, array([1.0, 2.0, 3.0]))
    assert_array_equal(result.curves[0].y, array([6.0, 36.0, 216.0]))

    for name, value in result.metadata.report.items():
        if name != MetaDataNames.persistent_result_files:
            assert value == model.get_output_data()[name]
        else:
            assert (value == model.get_output_data()[name]).all()


def test_simulation_without_analysis_node_run(tmp_wd):
    """A simulation executed outside an analysis node has no analysis node run."""
    model = create_model("MockModelPersistent", "LC1")
    model.execute()
    result = ModelResult.from_dict({
        "inputs": model.get_input_data(),
        "outputs": model.get_output_data(),
    })
    assert result.analysis_node_run_id == ""
    assert result.run_id


def test_superpose_curves(tmp_wd):
    """Check that the same curve coming from several results can be superposed."""
    xc = linspace(0, 1, 10)
    curves = [Curve({"xc": xc, "yc": alpha * xc}) for alpha in linspace(0.0, 1.0, 10)]
    result = ModelResult(
        curves=curves,
    )
    fig = superpose_curves(result.curves, show=False, save=True)
    assert Path("curves.html").exists()
    assert len(fig.data) == 10

    result.curves.append(Curve({"xd": xc, "yc": xc}))
    msg = (
        "Abscissa names are not unique: "
        "['xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xc', 'xd']"
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        superpose_curves(result.curves, show=False, save=True)


def test_superpose_curves_labels(tmp_wd):
    """The labels identify the sources, and the colours distinguish them."""
    xc = linspace(0, 1, 10)
    curves = [Curve({"xc": xc, "yc": alpha * xc}) for alpha in (0.5, 1.0)]
    fig = superpose_curves(curves, labels=["run 1", "run 2"], show=False, save=False)
    assert [trace.name for trace in fig.data] == ["run 1 - yc", "run 2 - yc"]
    assert fig.data[0].line.color != fig.data[1].line.color


def test_scalars_to_dataframe():
    """Check that a model result can plot scalars."""
    result = ModelResult(scalars={"x": 1.0, "y": 2.0, "s": "foo"})
    df = DataFrame([result.scalars()])
    expected_df = DataFrame([{"x": 1.0, "y": 2.0}])
    assert_frame_equal(df, expected_df)


def test_str():
    """A model result has a readable string representation."""
    result = ModelResult(
        scalars={"x": 1.0},
        vectors={"v": array([1.0, 2.0])},
        curves=[Curve({"xc": array([0.0, 1.0]), "yc": array([0.0, 1.0])})],
        fields={"pyramid": ["pyramid.vtk"]},
    )
    expected = "\nScalars:\n{'x': 1.0}\n\nVectors:\n{'v': array([1., 2.])}\n\nCurves:\n   ('xc', 'yc')\n         0    1\nxc  0.0  1.0\nyc  0.0  1.0\n   \nFields:\n{'pyramid': ['pyramid.vtk']}"
    assert str(result) == expected


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
    result = ModelResult.from_dict(model_data, load_fields=True)
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


def test_structured_model_result(tmp_wd):
    """The variables are told apart by group, the curves and figures by name."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.execute()
    model_data = {"inputs": model.get_input_data(), "outputs": model.get_output_data()}
    result = ModelResult.from_dict(model_data)

    assert result.scalars["height"] == pytest.approx(40.0)
    assert "height" in result.scalars(group="inputs")
    assert "height" not in result.scalars(group="outputs")
    assert "reaction_forces" in result.scalars(group="outputs")
    assert set(result.scalars(["height", "reaction_forces"])) == {
        "height",
        "reaction_forces",
    }
    with pytest.raises(ValueError, match="Unknown group"):
        result.scalars(group="parameters")

    assert result.curves["dplt_vs_dplt_grid"].variable_names == ("dplt_grid", "dplt")
    assert result.plots.names == ["dplt_vs_dplt_grid", "moment_vs_moment_grid"]
    assert result.plots["moment_vs_moment_grid"]["moment"].variable_names == (
        "moment_grid",
        "moment",
    )
    assert set(result.plot()) == set(result.plots.names)
    assert set(result.plot(plot_names=["dplt_vs_dplt_grid"])) == {"dplt_vs_dplt_grid"}

    assert result.run_id == model.get_output_data()[MetaDataNames.run_id][0]
    assert result.model_name == "BendingTestAnalytical"
    assert result.load_case == "Cantilever"
    assert result.study_name == "default_study"
    assert result.status == "FINISHED"


def test_to_dict_and_from_dict(tmp_wd):
    """The raw data of a result rebuilds an equal result."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.execute()
    result = ModelResult.from_dict({
        "inputs": model.get_input_data(),
        "outputs": model.get_output_data(),
    })
    raw = result.to_dict()
    assert set(raw) == {"inputs", "outputs", "metadata"}
    assert raw["inputs"]["height"] == pytest.approx(40.0)
    assert raw["metadata"][MetaDataNames.run_id] == result.run_id
    rebuilt = ModelResult.from_dict(raw, model=model)
    assert dict(rebuilt.scalars) == dict(result.scalars)
    assert rebuilt.curves.names == result.curves.names
