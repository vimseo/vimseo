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

"""Tests of the dashboard exploring the model results of an archive."""

from __future__ import annotations

from pathlib import Path

import pytest
from numpy import array

import vimseo.dashboards.main_dashboard as main_dashboard
from vimseo.api import create_model
from vimseo.api import open_model_results
from vimseo.dashboards.model_results.model_results_viewer_model import build_query
from vimseo.dashboards.model_results.model_results_viewer_model import (
    get_ignored_variations,
)
from vimseo.dashboards.model_results.model_results_viewer_model import get_input_names
from vimseo.dashboards.model_results.model_results_viewer_model import (
    get_variable_columns,
)
from vimseo.dashboards.model_results.model_results_viewer_model import plot_scalars
from vimseo.dashboards.model_results.model_results_viewer_model import select_families
from vimseo.dashboards.model_results.model_results_viewer_model import (
    summarize_families,
)
from vimseo.dashboards.model_results.model_results_viewer_model import to_python
from vimseo.utilities.test_utils import run_dashboard

ARCHIVE = "archive"

PAGE = Path(main_dashboard.__file__).parent / "pages" / "3_ModelResults.py"
"""The page exploring the model results of an archive."""


@pytest.fixture
def archive(tmp_wd) -> str:
    """A directory archive holding two simulations of a model in a study and one
    simulation of another model in another study."""
    model = create_model(
        "BendingTestAnalytical", "Cantilever", directory_archive_root=ARCHIVE
    )
    for young_modulus in (200000.0, 210000.0):
        model.execute({"young_modulus": array([young_modulus])})
    create_model(
        "MockMultiCurves",
        "Dummy",
        directory_archive_root=ARCHIVE,
        study_name="other_study",
    ).execute()
    return ARCHIVE


@pytest.fixture
def grid_archive(tmp_wd) -> str:
    """A directory archive holding the simulations of a model on a 2x2 grid of
    ``young_modulus`` and ``height``, and a simulation of another model."""
    model = create_model(
        "BendingTestAnalytical", "Cantilever", directory_archive_root=ARCHIVE
    )
    for young_modulus in (200000.0, 210000.0):
        for height in (40.0, 45.0):
            model.execute({
                "young_modulus": array([young_modulus]),
                "height": array([height]),
            })
    create_model("MockMultiCurves", "Dummy", directory_archive_root=ARCHIVE).execute()
    return ARCHIVE


def _open(archive: str):
    """Open the dashboard on an archive."""
    app = run_dashboard(PAGE)
    app.sidebar.text_input(key="directory_archive_root").set_value(archive).run()
    return app


def test_everything_is_listed_by_default(archive):
    """Without any filter, every result of the archive is listed."""
    app = _open(archive)
    assert not app.exception
    assert not app.error
    table = app.dataframe[0].value
    assert len(table) == 3
    assert set(table["model_name"]) == {"BendingTestAnalytical", "MockMultiCurves"}
    assert set(table["study_name"]) == {"default_study", "other_study"}


def test_refine_by_metadata_and_query(archive):
    """The results are refined from the values present in the archive."""
    app = _open(archive)
    models = app.sidebar.multiselect(key="model_name")
    assert models.options == ["BendingTestAnalytical", "MockMultiCurves"]
    models.set_value(["BendingTestAnalytical"]).run()
    assert len(app.dataframe[0].value) == 2

    app.sidebar.text_input(key="query").set_value(
        "`inputs.young_modulus` > 205000"
    ).run()
    assert not app.error
    assert len(app.dataframe[0].value) == 1

    app.multiselect(key="variable_columns").set_value(["inputs.young_modulus"]).run()
    assert "inputs.young_modulus" in app.dataframe[0].value.columns


def test_malformed_query(archive):
    """A malformed query is reported."""
    app = _open(archive)
    app.sidebar.text_input(key="query").set_value("height >").run()
    assert not app.exception
    assert "cannot be evaluated" in app.error[0].value


def test_empty_archive(tmp_wd):
    """An empty archive is reported."""
    app = _open("empty")
    assert not app.exception
    assert "no model result" in app.info[0].value


def test_build_query():
    """The empty selections keep everything."""
    assert build_query({"model_name": [], "status": []}) == ""
    assert (
        build_query({"model_name": ["A", "B"], "status": []}, "`inputs.x` > 1")
        == "`model_name` in ['A', 'B'] and (`inputs.x` > 1)"
    )


def test_plot_the_selected_results(archive):
    """The scalars of the selected results are plotted against each other."""
    model_results = open_model_results(directory_archive_root=archive)
    columns = get_variable_columns(model_results.summaries)
    assert "inputs.young_modulus" in columns
    figure = plot_scalars(
        model_results.filter(model_name="BendingTestAnalytical").summaries,
        ["inputs.young_modulus", "outputs.reaction_forces"],
    )
    assert len(figure.data[0].dimensions) == 2


def test_families(grid_archive):
    """The families of the results are listed along an input, and the chosen ones
    plotted."""
    model_results = open_model_results(directory_archive_root=grid_archive).filter(
        model_name="BendingTestAnalytical"
    )
    families = model_results.families("young_modulus")
    table = summarize_families(families)
    assert list(table["family"]) == ["height=40.0", "height=45.0"]
    assert list(table["n_results"]) == [2, 2]
    assert list(table["young_modulus"]) == [[200000.0, 210000.0]] * 2

    selected = select_families(families, ["height=45.0"])
    assert [str(key) for key in selected] == ["height=45.0"]
    assert all(name.endswith("[height=45.0]") for name in selected.visualize())


def test_get_input_names(grid_archive):
    """The names of the inputs are those of the columns without their prefix."""
    summaries = open_model_results(directory_archive_root=grid_archive).summaries
    names = get_input_names(summaries)
    assert {"young_modulus", "height"} <= set(names)
    assert not any(name.startswith("inputs.") for name in names)


def test_to_python():
    """The code reproduces the filter, the ignored inputs and the call."""
    archive = {"archive_manager": "DirectoryArchive", "directory_archive_root": ""}
    assert to_python(archive, "", []) == (
        "from vimseo.api import open_model_results\n\n"
        "open_model_results(archive_manager='DirectoryArchive')"
    )
    code = to_python(archive, "`status` in ['FINISHED']", ["x", "y"], "duplicates()")
    assert code.endswith(
        "open_model_results(archive_manager='DirectoryArchive')"
        ".filter(\"`status` in ['FINISHED']\").ignoring('x', 'y').duplicates()"
    )


def test_tabs_of_a_single_model(grid_archive):
    """The varying inputs, the families and the duplicates of a model are shown."""
    app = _open(grid_archive)
    assert "Select a single model" in app.info[1].value

    app.sidebar.multiselect(key="model_name").set_value(["BendingTestAnalytical"]).run()
    assert not app.exception
    assert not app.error
    assert set(app.dataframe[1].value.index) == {"height", "young_modulus"}

    app.selectbox(key="along").set_value("young_modulus").run()
    assert list(app.dataframe[2].value["family"]) == ["height=40.0", "height=45.0"]
    assert "families(along='young_modulus')" in app.code[2].value
    assert not app.get("plotly_chart")

    app.multiselect(key="family_keys").set_value(["height=40.0"]).run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3
    assert "No duplicate." in [info.value for info in app.info]

    app.sidebar.multiselect(key="ignored_inputs").set_value(["height"]).run()
    assert not app.exception
    assert len(app.dataframe[-1].value) == 4
    assert ".ignoring('height').duplicates()" in app.code[-1].value


def test_ignored_input_varying_in_a_family(grid_archive):
    """An ignored input varying in a family is reported, with its values."""
    model_results = open_model_results(directory_archive_root=grid_archive).filter(
        model_name="BendingTestAnalytical"
    )
    families = model_results.families("height")
    assert not get_ignored_variations(families)
    table = summarize_families(families)
    assert "young_modulus (ignored)" not in table.columns
    assert not table["repeated_along"].any()

    families = model_results.ignoring("young_modulus").families("height")
    assert get_ignored_variations(families) == {"all": ["young_modulus"]}
    table = summarize_families(families)
    (heights,) = table["height"]
    (young_moduli,) = table["young_modulus (ignored)"]
    assert sorted(zip(heights, young_moduli, strict=True)) == [
        (40.0, 200000.0),
        (40.0, 210000.0),
        (45.0, 200000.0),
        (45.0, 210000.0),
    ]
    assert table["repeated_along"].all()


def test_warning_of_an_ignored_input_varying_in_a_family(grid_archive):
    """The dashboard warns when an ignored input varies in a family."""
    app = _open(grid_archive)
    app.sidebar.multiselect(key="model_name").set_value(["BendingTestAnalytical"]).run()
    app.sidebar.multiselect(key="ignored_inputs").set_value(["young_modulus"]).run()
    app.selectbox(key="along").set_value("height").run()
    assert not app.exception
    assert "`young_modulus`" in app.warning[0].value

    app.multiselect(key="family_keys").set_value(["all"]).run()
    assert not app.exception
    assert "repeated" in app.caption[0].value
