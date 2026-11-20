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

"""Tests of the dashboard editing a parameter space."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import vimseo.dashboards.main_dashboard as main_dashboard
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.api import create_model
from vimseo.dashboards.visualisation.result_loader import ResultSource
from vimseo.io.space_io import SpaceAnalysisNodeFileIO

TIMEOUT = 300

VARIABLE_NAMES = ["young_modulus", "nu_p"]
"""Variables of the model, the first one having a lower and an upper bound, the second
one having none."""

BUILDERS_REQUIRING_MODEL_BOUNDS = ("FromModelMinAndMax",)
"""The space builders requiring the variables to have bounds in the model."""


@pytest.fixture
def space_result_path(tmp_wd) -> Path:
    """The file of a parameter space on inputs of the model of the dashboard."""
    analysis_node = SpaceAnalysisNode()
    analysis_node.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromModelCenterAndCov",
        model=create_model("BendingTestAnalytical", "Cantilever"),
        variable_names=["young_modulus", "nu_p"],
        use_default_values_as_center=True,
        cov=0.05,
    )
    analysis_node.save_results()
    return analysis_node.working_directory / "SpaceAnalysisNode_result.hdf5"


def test_set_initial_parameter_space(space_result_path):
    """A loaded parameter space is set and its distributions are plotted."""
    app = AppTest.from_file(
        str(Path(main_dashboard.__file__).parent / "pages" / "2_ParameterSpace.py"),
        default_timeout=TIMEOUT,
    )
    app.run()
    assert not app.exception

    app.radio(key="space_result_source").set_value(ResultSource.URI).run()
    app.text_input(key="space_result_uri").set_value(str(space_result_path)).run()
    assert not app.exception

    next(
        button
        for button in app.button
        if button.label == "Set to initial parameter space"
    ).click().run()
    assert not app.exception
    # A figure per variable of the parameter space.
    assert len(app.get("plotly_chart")) >= 2


def _get_builders_and_distributions() -> list[tuple[str, str]]:
    """Return the pairs of space builder and distribution offered by the dashboard."""
    from vimseo.analysis_nodes.lib.space_builder_factory import SpaceBuilderFactory
    from vimseo.dashboards.space.space_dashboard_model import get_space_builder_names

    return [
        (builder_name, distribution_name)
        for builder_name in get_space_builder_names()
        for distribution_name in SpaceBuilderFactory()
        .create(builder_name)
        .get_available_distributions()
    ]


def _build_space(builder_name: str, distribution_name: str, variable_names) -> AppTest:
    """Build a parameter space from the form of the dashboard."""
    app = AppTest.from_file(
        str(Path(main_dashboard.__file__).parent / "pages" / "2_ParameterSpace.py"),
        default_timeout=TIMEOUT,
    )
    app.run()
    app.multiselect(key="variable_names").set_value(variable_names).run()
    app.selectbox(key="space_builder_name").set_value(builder_name).run()
    app.selectbox(key="distribution_name").set_value(distribution_name).run()
    next(
        button for button in app.button if button.label == "Submit space parameters"
    ).click().run()
    return app


@pytest.mark.parametrize(
    ("builder_name", "distribution_name"), _get_builders_and_distributions()
)
def test_space_builder(tmp_wd, builder_name, distribution_name):
    """A parameter space is built from the form of each space builder."""
    variable_names = (
        VARIABLE_NAMES[:1]
        if builder_name in BUILDERS_REQUIRING_MODEL_BOUNDS
        else VARIABLE_NAMES
    )
    app = _build_space(builder_name, distribution_name, variable_names)
    assert not app.exception
    assert not app.error
    assert not [w for w in app.warning if "empty" in w.value]
    parameter_space = app.session_state["space_analysis_node"].result.parameter_space
    assert parameter_space.variable_names == variable_names
    assert len(app.get("plotly_chart")) == len(variable_names)

    # The parameter space can be downloaded in HDF5 and JSON formats.
    assert len(app.get("download_button")) == 2
    result = app.session_state["space_analysis_node"].result
    json_result = SpaceAnalysisNodeFileIO().read_buffer(
        SpaceAnalysisNodeFileIO().write(result)
    )
    assert json_result.parameter_space.variable_names == variable_names


def test_space_builder_error(tmp_wd):
    """An error of the space builder is shown, rather than breaking the page."""
    app = _build_space("FromModelMinAndMax", "OTUniformDistribution", ["nu_p"])
    assert not app.exception
    assert "no lower and upper bounds" in app.error[0].value
