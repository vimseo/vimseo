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

"""Tests of the dashboard exploring the archive of the simulations of a model."""

from __future__ import annotations

from pathlib import Path

import pytest
from numpy import array

from vimseo.api import create_model
from vimseo.utilities.test_utils import run_dashboard

# The dashboards require the ``dashboard`` extra.
pytest.importorskip("streamlit")

import vimseo.dashboards.database_viewer.db_viewer as db_viewer  # ruff: ignore[module-import-not-at-top-of-file]

MODEL_NAME = "BendingTestAnalytical"
LOAD_CASE_NAME = "Cantilever"
ARCHIVE = "db"


@pytest.fixture
def archive(tmp_wd) -> str:
    """A directory archive holding two simulations of a model."""
    model = create_model(MODEL_NAME, LOAD_CASE_NAME, directory_archive_root=ARCHIVE)
    for young_modulus in (200000.0, 210000.0):
        model.execute({"young_modulus": array([young_modulus])})
    return ARCHIVE


def test_explore_an_experiment(archive):
    """The simulations of an experiment are listed, with default variables."""
    app = run_dashboard(Path(db_viewer.__file__))
    app.sidebar.selectbox(key="model_name").set_value(MODEL_NAME).run()
    app.sidebar.selectbox(key="lc_name").set_value(LOAD_CASE_NAME).run()
    app.sidebar.text_input(key="uri").set_value(archive).run()
    app.sidebar.text_input(key="experiment_name").set_value(
        f"{MODEL_NAME}/{LOAD_CASE_NAME}"
    ).run()
    next(
        button
        for button in app.button
        if button.label == "Set default variables for exploration"
    ).click().run()

    assert not app.exception
    assert not app.error
    table = app.dataframe[0].value
    assert len(table) == 2
    assert "cpu_time" in table.columns
