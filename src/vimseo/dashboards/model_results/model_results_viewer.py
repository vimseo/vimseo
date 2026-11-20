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

"""The page exploring the model results of an archive.

Every model result of the archive is listed, whatever its study, model and load case;
the user then refines the selection from the values present in the archive.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from vimseo.api import open_model_results
from vimseo.dashboards.model_results.model_results_viewer_model import ARCHIVE_MANAGERS
from vimseo.dashboards.model_results.model_results_viewer_model import DEFAULT_COLUMNS
from vimseo.dashboards.model_results.model_results_viewer_model import METADATA_FILTERS
from vimseo.dashboards.model_results.model_results_viewer_model import build_query
from vimseo.dashboards.model_results.model_results_viewer_model import (
    get_ignored_variations,
)
from vimseo.dashboards.model_results.model_results_viewer_model import get_input_names
from vimseo.dashboards.model_results.model_results_viewer_model import get_values
from vimseo.dashboards.model_results.model_results_viewer_model import (
    get_variable_columns,
)
from vimseo.dashboards.model_results.model_results_viewer_model import initialize
from vimseo.dashboards.model_results.model_results_viewer_model import plot_scalars
from vimseo.dashboards.model_results.model_results_viewer_model import select_families
from vimseo.dashboards.model_results.model_results_viewer_model import (
    summarize_families,
)
from vimseo.dashboards.model_results.model_results_viewer_model import to_python

if TYPE_CHECKING:
    from collections.abc import Callable

    from vimseo.results.collection import ModelResults


@st.cache_resource
def _open_model_results(archive_manager: str, directory_archive_root: str):
    """Open the model results of an archive, once per archive."""
    return open_model_results(archive_manager, directory_archive_root)


def model_results_viewer() -> None:
    initialize(st.session_state)

    st.sidebar.selectbox("Archive manager", ARCHIVE_MANAGERS, key="archive_manager")
    st.sidebar.text_input(
        "Root directory of the archive",
        key="directory_archive_root",
        help="If empty, the one of the configuration.",
    )
    if st.sidebar.button("Reload the archive"):
        _open_model_results.clear()

    root = st.session_state.directory_archive_root
    try:
        # The absolute path tells apart the archives of a relative root opened from
        # different working directories, which the cache would mix up.
        model_results = _open_model_results(
            st.session_state.archive_manager, str(Path(root).resolve()) if root else ""
        )
    except Exception as error:  # ruff: ignore[blind-except]
        st.error(f"The archive cannot be opened: {error}")
        return

    if not len(model_results):
        st.info("There is no model result in this archive.")
        return

    summaries = model_results.summaries
    for name, label in METADATA_FILTERS.items():
        st.sidebar.multiselect(
            label,
            get_values(summaries, name),
            key=name,
            help="If empty, all of them.",
        )
    st.sidebar.text_input(
        "Query",
        key="query",
        help="E.g. `inputs.height` > 45 or load_case == 'ThreePoints'",
    )

    query = build_query(
        {name: st.session_state[name] for name in METADATA_FILTERS},
        st.session_state.query,
    )
    try:
        model_results = model_results.filter(query)
    except ValueError as error:
        st.error(str(error))
        return

    n_results = len(summaries)
    st.sidebar.multiselect(
        "Ignored inputs",
        get_input_names(model_results.summaries),
        key="ignored_inputs",
        help="Left out of the varying inputs, the families and the duplicates.",
    )
    ignored = st.session_state.ignored_inputs
    model_results = model_results.ignoring(*ignored)
    st.write(f"{len(model_results)} model results out of {n_results}.")

    archive = {
        "archive_manager": st.session_state.archive_manager,
        "directory_archive_root": st.session_state.directory_archive_root,
    }

    def show_code(call: str = "") -> None:
        """Show the Python code computing what a tab shows."""
        st.code(to_python(archive, query, ignored, call), language="python")

    tabs = st.tabs(["Results", "Varying inputs", "Families", "Duplicates"])
    with tabs[0]:
        _show_results(model_results)
        show_code()
    single_model = len(get_values(model_results.summaries, "model_name")) <= 1
    for tab, show in zip(
        tabs[1:],
        (_show_varying_inputs, _show_families, _show_duplicates),
        strict=True,
    ):
        with tab:
            if single_model:
                show(model_results, show_code)
            else:
                st.info("Select a single model to compare its results.")


def _show_results(model_results: ModelResults) -> None:
    """Show the table of the results and plot the selected ones."""
    summaries = model_results.summaries
    st.multiselect(
        "Inputs and outputs to show",
        get_variable_columns(summaries),
        key="variable_columns",
    )
    columns = [
        *(column for column in DEFAULT_COLUMNS if column in summaries.columns),
        *st.session_state.variable_columns,
    ]
    event = st.dataframe(
        summaries[columns],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="table",
    )
    selected_rows = event.selection.rows
    if not selected_rows:
        st.info("Select some results in the table to plot them.")
        return

    run_ids = list(summaries["run_id"].iloc[selected_rows])
    selected = model_results.filter(f"run_id in {run_ids!r}")
    if st.session_state.variable_columns:
        st.plotly_chart(
            plot_scalars(selected.summaries, st.session_state.variable_columns),
            use_container_width=True,
        )
    if len(get_values(selected.summaries, "model_name")) > 1:
        st.info("The curves are superposed for the results of a single model.")
        return

    for name, figure in selected.visualize().items():
        st.plotly_chart(figure, use_container_width=True, key=f"curves_{name}")


def _show_varying_inputs(
    model_results: ModelResults, show_code: Callable[[str], None]
) -> None:
    """Show the inputs taking several values."""
    varying_inputs = model_results.varying_inputs()
    if varying_inputs.empty:
        st.info("No input varies.")
    else:
        st.dataframe(varying_inputs, use_container_width=True)
    show_code("varying_inputs()")


def _show_families(
    model_results: ModelResults, show_code: Callable[[str], None]
) -> None:
    """Show the families of results differing by a single input and plot some."""
    names = list(model_results.varying_inputs().index)
    if not names:
        st.info("No input varies: there is no family.")
        return

    along = st.selectbox("Along", names, key="along")
    try:
        families = model_results.families(along)
    except (KeyError, ValueError) as error:
        st.error(str(error))
        return

    show_code(f"families(along={along!r})")
    n_ungrouped = len(families.ungrouped)
    st.write(
        f"{len(families)} families varying `{along}`, "
        f"{n_ungrouped} results in no family."
    )
    if not len(families):
        return

    table = summarize_families(families)
    st.dataframe(table, use_container_width=True, hide_index=True)
    variations = get_ignored_variations(families)
    if variations:
        names = sorted({name for names in variations.values() for name in names})
        n_families = len(variations)
        st.warning(
            f"In {n_families} {'family' if n_families == 1 else 'families'}, "
            "the ignored inputs "
            f"{', '.join(f'`{name}`' for name in names)} vary: their results are "
            "compared as if these inputs were equal, so the figures may join points "
            f"with the same value of `{along}`."
        )
    st.download_button(
        "Download the results of the families (CSV)",
        families.to_dataframe().to_csv(),
        file_name=f"families_along_{along}.csv",
        mime="text/csv",
    )
    keys = [str(key) for key in families]
    st.session_state.family_keys = [
        key for key in st.session_state.family_keys if key in keys
    ]
    st.multiselect("Families to plot", keys, key="family_keys")
    repeated = [
        key
        for key, is_repeated in zip(
            table["family"], table["repeated_along"], strict=True
        )
        if is_repeated and key in st.session_state.family_keys
    ]
    if repeated:
        st.caption(
            f"Some values of `{along}` are repeated in the families {repeated}: "
            "the curves join the results of different values of the ignored inputs."
        )
    for name, figure in (
        select_families(families, st.session_state.family_keys).visualize().items()
    ):
        st.plotly_chart(figure, use_container_width=True, key=f"family_{name}")


def _show_duplicates(
    model_results: ModelResults, show_code: Callable[[str], None]
) -> None:
    """Show the groups of results with the same inputs."""
    duplicates = model_results.duplicates()
    if duplicates.empty:
        st.info("No duplicate.")
    else:
        st.dataframe(duplicates, use_container_width=True, hide_index=True)
    show_code("duplicates()")
