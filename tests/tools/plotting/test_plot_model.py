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

# Copyright (c) 2024 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - initial API and implementation and/or
#    initial documentation
#        :author: Benedicte REINE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from vimseo.api import create_model
from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.core.model_result import ModelResult
from vimseo.tools.post_tools.plot_parameters import DEFAULT_AXIS_COLOR
from vimseo.tools.post_tools.plot_parameters import create_plot


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

    expected_plots = [
        create_plot(plot)
        for plot in list(model.load_case.plot_parameters.plots) + list(model.PLOTS)
    ]
    assert model.plots == expected_plots

    for plot in expected_plots:
        assert plot.get_name() in figures
        assert Path(
            model.archive_manager.job_directory
            / f"{model.name}_{load_case}_{plot.get_file_name()}"
        ).is_file()


def test_plot_model_multi_curves(tmp_wd):
    """Check the figures holding several lines, a twin axis and a constant line."""
    model = create_model("MockMultiCurves", "Dummy")
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
        "critical energy",
    ]
    # The force is drawn against the primary axis, the two others against the
    # secondary one.
    assert [trace.yaxis for trace in crack.data] == ["y", "y2", "y2"]
    # An ordinate axis holding a single line takes its colour.
    assert crack.layout.yaxis.title.font.color == "blue"
    assert crack.layout.yaxis2.title.font.color == DEFAULT_AXIS_COLOR
    # The constant line is resolved from the value of the model variable.
    assert list(crack.data[2].y) == [0.5, 0.5]
    # The markers and the dash patterns are those prescribed by the styles.
    assert crack.data[0].mode == "lines+markers"
    assert crack.data[1].line.dash == "dash"


def test_plot_model_select_variables(tmp_wd):
    """Check that a subset of the lines of a figure can be drawn."""
    model = create_model("MockMultiCurves", "Dummy")
    model.execute()
    result = ModelResult.from_data(
        {"inputs": model.get_input_data(), "outputs": model.get_output_data()},
        model=model,
    )
    fig = result.plots[0].plot(
        variable_names=["energy_strain_history"], show=False, save=False
    )
    assert [trace.name for trace in fig.data] == ["energy_strain_history"]


def test_curves_attribute_raises():
    """Check that a model still declaring CURVES is rejected."""
    msg = "The class attribute CURVES of ObsoleteModel has been replaced by PLOTS"
    with pytest.raises(AttributeError, match=msg):

        class ObsoleteModel(BaseDisciplineModel):
            CURVES: ClassVar[list[tuple[str, str]]] = [("x", "y")]


def test_plot_model_scalars():
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
