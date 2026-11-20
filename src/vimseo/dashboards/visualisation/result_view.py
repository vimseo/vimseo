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

"""The display of the tables and the figures of an analysis node result."""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any

import streamlit as st

from vimseo.analysis_nodes.result_visualization import _is_matplotlib_figure
from vimseo.analysis_nodes.result_visualization import get_file_stem
from vimseo.analysis_nodes.result_visualization import save_figures

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from pandas import DataFrame

    from vimseo.analysis_nodes.base_result import BaseResult
    from vimseo.analysis_nodes.result_visualization import Figure

MAX_DEFAULT_FIGURES = 6
"""The maximum number of figures shown by default."""

_COMPONENT = re.compile(r"^(?P<name>.+)\[\d+\]$")
"""The pattern of a column holding a component of a vector, e.g. ``dplt[0]``."""


def group_columns_by_variable(table: DataFrame) -> dict[str, list[str]]:
    """Return the columns of a table grouped by variable.

    A vector is stored in a column per component, ``name[0]``, ``name[1]``...; any
    other column is a variable on its own.

    Args:
        table: The table.

    Returns:
        The columns of each variable, in the order of the columns.
    """
    variables = {}
    for column in map(str, table.columns):
        match = _COMPONENT.match(column)
        variables.setdefault(match["name"] if match else column, []).append(column)
    return variables


def filter_columns(
    table: DataFrame, variable_names: Iterable[str] = (), scalars_only: bool = False
) -> DataFrame:
    """Return the columns of some variables of a table.

    Args:
        table: The table.
        variable_names: The names of the variables. If empty, all of them.
        scalars_only: Whether to keep only the variables held by a single column.

    Returns:
        The selected columns, named as text.
    """
    variable_names = set(variable_names)
    columns = [
        column
        for name, variable_columns in group_columns_by_variable(table).items()
        if (not variable_names or name in variable_names)
        and (not scalars_only or len(variable_columns) == 1)
        for column in variable_columns
    ]
    table = table.copy()
    table.columns = table.columns.map(str)
    return table[columns]


def get_result_key(result: BaseResult) -> str:
    """Return a key identifying a loaded analysis node result in the caches.

    The loaded results are cached, so a result keeps its identity while it is
    displayed.
    """
    return (
        f"{type(result).__name__}_{result.metadata.analysis_node_run_id}_{id(result)}"
    )


@st.cache_resource(show_spinner="Creating the figures...")
def plot(_result: BaseResult, result_key: str, **options: Any) -> dict[str, Figure]:
    """Create the figures of an analysis node result, once per result and settings.

    Args:
        _result: The analysis node result.
        result_key: The key identifying the result, see :func:`get_result_key`.
        **options: The settings of the figures.
    """
    return _result.plot(**options)


@st.cache_data(show_spinner="Computing the tables...")
def to_dataframes(_result: BaseResult, result_key: str) -> dict[str, DataFrame]:
    """Return the tables of an analysis node result, once per result.

    Args:
        _result: The analysis node result.
        result_key: The key identifying the result, see :func:`get_result_key`.
    """
    return _result.to_dataframes()


def _to_displayable(table: DataFrame) -> DataFrame:
    """Return a table whose columns mixing types are converted to text.

    Arrow, used by Streamlit to display a table, requires a type per column.
    """
    table = table.copy()
    for column in table.columns:
        if table[column].dtype == object:
            table[column] = table[column].map(
                lambda value: "" if value is None else str(value)
            )
    return table


def _st_filter_columns(table: DataFrame, key: str) -> DataFrame:
    """Select the variables of a table to display.

    The vectors are left out by default, since a column per component makes the table
    unreadable.

    Args:
        table: The table.
        key: A prefix making the keys of the widgets unique.

    Returns:
        The selected columns.
    """
    variables = group_columns_by_variable(table)
    if len(variables) < 2:
        return table

    scalars_only = False
    if any(len(columns) > 1 for columns in variables.values()):
        scalars_only = st.checkbox(
            "Scalars only",
            value=True,
            help="Leave out the vectors, stored in a column per component.",
            key=f"{key}_scalars_only",
        )
    variable_names = st.multiselect(
        "Variables",
        [
            name
            for name, columns in variables.items()
            if not scalars_only or len(columns) == 1
        ],
        placeholder="All",
        key=f"{key}_variables",
    )
    filtered_table = filter_columns(table, variable_names, scalars_only)
    if filtered_table.shape[1] < table.shape[1]:
        st.caption(f"{filtered_table.shape[1]} of {table.shape[1]} columns.")
    return filtered_table


def render_tables(tables: Mapping[str, DataFrame], key: str) -> None:
    """Display tables, with a button to download each one as CSV.

    The variables of a table can be selected, the vectors being left out by default;
    the table is downloaded as displayed.

    Args:
        tables: The tables.
        key: A prefix making the keys of the widgets unique.
    """
    if not tables:
        st.info("This result has no table.")
        return

    for name, table in tables.items():
        st.markdown(f"#### {name}")
        table = _st_filter_columns(table, f"{key}_{name}")
        st.dataframe(_to_displayable(table), use_container_width=True)
        st.download_button(
            "Download as CSV",
            table.to_csv().encode(),
            file_name=f"{get_file_stem(name)}.csv",
            mime="text/csv",
            key=f"{key}_download_{name}",
        )


def _zip_figures(figures: Mapping[str, Figure]) -> bytes:
    """Return a zip archive of figures, in html for plotly and png for matplotlib."""
    buffer = BytesIO()
    with (
        TemporaryDirectory() as directory_path,
        zipfile.ZipFile(buffer, "w") as zip_file,
    ):
        for path in save_figures(figures, directory_path):
            zip_file.write(path, path.name)
    return buffer.getvalue()


def render_figure(figure: Figure, key: str) -> None:
    """Display a plotly or a matplotlib figure.

    Args:
        figure: The figure.
        key: The key of the widget.
    """
    if _is_matplotlib_figure(figure):
        st.pyplot(figure, use_container_width=True)
    else:
        st.plotly_chart(figure, use_container_width=True, key=key)


def render_figures(figures: Mapping[str, Figure], key: str) -> None:
    """Display figures selected by their keys, with a button to download them.

    Args:
        figures: The figures.
        key: A prefix making the keys of the widgets unique.
    """
    if not figures:
        st.info("This result has no figure.")
        return

    names = list(figures)
    selected_names = st.multiselect(
        "Figures",
        names,
        default=names[:MAX_DEFAULT_FIGURES],
        key=f"{key}_figure_names",
    )
    if selected_names:
        for name, tab in zip(selected_names, st.tabs(selected_names), strict=True):
            with tab:
                render_figure(figures[name], f"{key}_figure_{name}")

    if st.button("Prepare the download of the selected figures", key=f"{key}_zip"):
        st.download_button(
            "Download the figures",
            _zip_figures({name: figures[name] for name in selected_names}),
            file_name="figures.zip",
            mime="application/zip",
            key=f"{key}_download_figures",
        )


def st_plot_choices(result: BaseResult, key: str) -> dict[str, str | tuple[str, ...]]:
    """Select the names proposed by a result for the settings of its figures.

    A setting left empty means its default value, e.g. all the names.

    Args:
        result: The analysis node result.
        key: A prefix making the keys of the widgets unique.

    Returns:
        The selected names, bound to the names of the settings.
    """
    choices = result.get_plot_choices()
    if not choices:
        return {}

    settings_class = type(result)._PLOT_SETTINGS
    options = {}
    with st.expander("Figure settings"):
        for name, values in choices.items():
            field = settings_class.model_fields[name]
            label = name.replace("_", " ").capitalize()
            if field.annotation is str:
                # A setting selecting a single name, empty by default.
                options[name] = st.selectbox(
                    label,
                    ["", *values],
                    help=field.description,
                    format_func=lambda value: value or "Default",
                    key=f"{key}_{name}",
                )
            else:
                options[name] = tuple(
                    st.multiselect(
                        label,
                        values,
                        help=field.description,
                        placeholder="All",
                        key=f"{key}_{name}",
                    )
                )
    return options


def render_result(result: BaseResult, key: str, **options: Any) -> None:
    """Display the tables and the figures of an analysis node result.

    Args:
        result: The analysis node result.
        key: A prefix making the keys of the widgets unique.
        **options: The settings of the figures.
    """
    result_key = get_result_key(result)
    values_tab, figures_tab = st.tabs(["Values", "Figures"])
    with values_tab:
        render_tables(to_dataframes(result, result_key), key)
    with figures_tab:
        options = {**st_plot_choices(result, key), **options}
        render_figures(plot(result, result_key, **options), key)
