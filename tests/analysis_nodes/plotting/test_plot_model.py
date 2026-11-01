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

from pathlib import Path
from typing import ClassVar

import pytest

from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import DEFAULT_AXIS_COLOR
from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import create_plot
from vimseo.api import create_model
from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.core.model_result import ModelResult


@pytest.mark.parametrize(
    ("model", "load_case"),
    [
        ("BendingTestAnalytical", "Cantilever"),
        ("MockModel", "LC2"),
    ],
)
def test_plot_model(tmp_wd, model, load_case):
    """Check that the figures of a model are correctly plotted."""
    model = create_model(model, load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    figures = model.plot_results()

    model_keys = {create_plot(p).get_key() for p in model.PLOTS}
    load_case_keys = {create_plot(p).get_key() for p in model.load_case.PLOTS}
    assert {plot.get_key() for plot in model.plots} == model_keys | load_case_keys

    for plot in model.plots:
        assert plot.get_name() in figures
        assert Path(
            model.archive_manager.job_directory / plot.get_file_name()
        ).is_file()


def test_plot_model_multi_curves(tmp_wd):
    """Check the figures holding several lines, a twin axis and a constant line."""
    # A short archive root: the name of the figure of the energies is long, and the
    # temporary directories of pytest-xdist too, while Windows limits paths to 260
    # characters.
    model = create_model("MockMultiCurves", "Dummy", directory_archive_root="a")
    model.execute()
    figures = model.plot_results()

    energies = figures["energy_strain_history_and_2_more_vs_displacement_history"]
    assert [trace.name for trace in energies.data] == [
        "energy_strain_history",
        "energy_damage_history",
        "energy_viscous_history",
    ]
    # A single ordinate axis holding several lines takes the default colour.
    assert energies.layout.yaxis.title.font.color == DEFAULT_AXIS_COLOR

    crack = figures["crack_propagation"]
    assert [trace.name for trace in crack.data] == [
        "force",
        "crack position",
        "critical crack position",
    ]
    # The force is drawn against the primary axis, the two others against the
    # secondary one.
    assert [trace.yaxis for trace in crack.data] == ["y", "y2", "y2"]
    # An ordinate axis holding a single line takes its colour.
    assert crack.layout.yaxis.title.font.color == "blue"
    assert crack.layout.yaxis2.title.font.color == DEFAULT_AXIS_COLOR
    # The constant line is resolved from the value of the model variable.
    assert list(crack.data[2].y) == [35.0, 35.0]
    # The markers and the dash patterns are those prescribed by the styles.
    assert crack.data[0].mode == "lines+markers"
    assert crack.data[1].line.dash == "dash"


def test_plot_model_select_variables(tmp_wd):
    """Check that a subset of the lines of a figure can be drawn."""
    model = create_model("MockMultiCurves", "Dummy")
    model.execute()
    result = ModelResult.from_dict(
        {"inputs": model.get_input_data(), "outputs": model.get_output_data()},
        model=model,
    )
    fig = result.plots[0].plot(
        variable_names=["energy_strain_history"], show=False, save=False
    )
    assert [trace.name for trace in fig.data] == ["energy_strain_history"]


def test_plot_model_plots_override(tmp_wd):
    """Check that a load case PLOTS overrides/extends the model PLOTS end-to-end."""
    model = create_model("MockCurvesOverride", "DummyOverride")
    model.execute()
    plots = model.plots

    keys = [p.get_key() for p in plots]
    assert keys == [("x_history", "y_history"), ("x_history", "y_2_history")]
    assert plots[0].title == "Overridden plot"


def test_curves_attribute_raises():
    """Check that a model still declaring CURVES is rejected."""
    msg = "The class attribute CURVES of ObsoleteModel has been replaced by PLOTS"
    with pytest.raises(AttributeError, match=msg):

        class ObsoleteModel(BaseDisciplineModel):
            CURVES: ClassVar[list[tuple[str, str]]] = [("x", "y")]


def test_plot_model_scalars(tmp_wd):
    """Check that the scalar outputs of a model can be plotted in a scatter matrix.

    A non-existing directory is passed to also check that it is created.
    """
    m = create_model("MockModel", "LC2")
    m.EXTRA_INPUT_GRAMMAR_CHECK = True
    m.execute()
    plot_dir = "plots_subdir"
    figures = m.plot_results(directory_path=plot_dir, data="SCALARS", save=True)
    assert (Path(plot_dir) / "scalars.png").is_file()
    assert "scalars" in figures


def test_plot_model_unknown_data_type_raises(tmp_wd):
    """Check that an unknown data type to plot raises."""
    m = create_model("MockModel", "LC2")
    m.EXTRA_INPUT_GRAMMAR_CHECK = True
    m.execute()
    with pytest.raises(ValueError, match="Unknown data type"):
        m.plot_results(data="BOGUS")
