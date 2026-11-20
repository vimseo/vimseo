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

"""The logic of the dashboard exploring the model results of an archive."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from pandas import DataFrame

from vimseo.results.collection import Families
from vimseo.results.operations import INPUT_PREFIX
from vimseo.results.operations import OUTPUT_PREFIX

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from plotly.graph_objects import Figure

ARCHIVE_MANAGERS = ("DirectoryArchive", "MlflowArchive")
"""The archive managers proposed by the dashboard."""

METADATA_FILTERS = {
    "study_name": "Studies",
    "model_name": "Models",
    "load_case": "Load cases",
    "status": "Statuses",
}
"""The metadata refining the results, bound to their labels."""

DEFAULT_COLUMNS = ("run_id", "datetime", *METADATA_FILTERS)
"""The columns of the table of the results shown by default."""


def initialize(session_state: Mapping) -> None:
    """Set the default values of the state of the dashboard.

    Everything is empty by default, meaning that every result of the archive is
    shown.

    Args:
        session_state: The state of the dashboard.
    """
    variables = {
        "archive_manager": ARCHIVE_MANAGERS[0],
        "directory_archive_root": "",
        "query": "",
        "variable_columns": [],
        "ignored_inputs": [],
        "family_keys": [],
        **{name: [] for name in METADATA_FILTERS},
    }
    for name, default in variables.items():
        if name not in session_state:
            session_state[name] = default


def get_values(summaries: DataFrame, column: str) -> list[str]:
    """Return the values of a metadata present in the summaries.

    Args:
        summaries: The summaries of the results.
        column: The column of the metadata.

    Returns:
        The sorted values, empty if the column is missing.
    """
    if column not in summaries.columns:
        return []
    return sorted(summaries[column].dropna().astype(str).unique())


def get_variable_columns(summaries: DataFrame) -> list[str]:
    """Return the columns of the inputs and the outputs.

    Args:
        summaries: The summaries of the results.

    Returns:
        The columns ``inputs.{name}`` then ``outputs.{name}``.
    """
    return [
        column
        for prefix in (INPUT_PREFIX, OUTPUT_PREFIX)
        for column in summaries.columns
        if column.startswith(prefix)
    ]


def build_query(selections: Mapping[str, Sequence[str]], query: str = "") -> str:
    """Return the query selecting the results.

    Args:
        selections: The values of metadata to keep, bound to the metadata.
            An empty selection keeps every value.
        query: A query added to the selections, see :mod:`vimseo.results.query`.

    Returns:
        The query, empty when everything is kept.
    """
    terms = [
        f"`{name}` in {list(values)!r}" for name, values in selections.items() if values
    ]
    if query.strip():
        terms.append(f"({query})")
    return " and ".join(terms)


def plot_scalars(summaries: DataFrame, columns: Sequence[str]) -> Figure:
    """Plot the scalars of some results against each other.

    Args:
        summaries: The summaries of the results.
        columns: The columns of the scalars.

    Returns:
        A scatter matrix, whose points are labelled by the identifiers of the results.
    """
    import plotly.express as px

    return px.scatter_matrix(summaries, dimensions=list(columns), hover_name="run_id")


def get_input_names(summaries: DataFrame) -> list[str]:
    """Return the names of the inputs.

    Args:
        summaries: The summaries of the results.

    Returns:
        The names of the inputs, without the prefix of their columns.
    """
    return [
        column[len(INPUT_PREFIX) :]
        for column in summaries.columns
        if column.startswith(INPUT_PREFIX)
    ]


def summarize_families(families: Families) -> DataFrame:
    """Summarize the families of results, one row per family.

    Args:
        families: The families.

    Returns:
        The key of each family, its number of results, the values of the input varying
        in the family, whether some of them are repeated, the values of the ignored
        inputs varying in a family, in the column ``{name} (ignored)``, and the
        identifiers of its results.
    """
    along = families.along
    ignored_names = list(
        dict.fromkeys(
            name
            for names in get_ignored_variations(families).values()
            for name in names
        )
    )
    columns = [
        "family",
        "n_results",
        along,
        "repeated_along",
        *(f"{name} (ignored)" for name in ignored_names),
        "run_ids",
    ]
    rows = []
    for key, family in families.items():
        summaries = family.summaries
        values = summaries[f"{INPUT_PREFIX}{along}"]
        rows.append({
            "family": str(key),
            "n_results": len(family),
            along: list(values),
            "repeated_along": bool(values.duplicated().any()),
            **{
                f"{name} (ignored)": list(summaries[f"{INPUT_PREFIX}{name}"])
                for name in ignored_names
            },
            "run_ids": list(summaries["run_id"]),
        })
    return DataFrame(rows, columns=columns)


def get_ignored_variations(families: Families) -> dict[str, list[str]]:
    """Return the ignored inputs varying in each family.

    The results of such a family are compared as if these inputs were equal.

    Args:
        families: The families.

    Returns:
        The names of the ignored inputs taking several values in a family, bound to the
        key of the family, as a string; the families without any are left out.
    """
    variations = {}
    for key, family in families.items():
        summaries = family.summaries
        names = [
            name
            for name in families.ignoring
            if f"{INPUT_PREFIX}{name}" in summaries.columns
            and summaries[f"{INPUT_PREFIX}{name}"].nunique(dropna=True) > 1
        ]
        if names:
            variations[str(key)] = names
    return variations


def select_families(families: Families, keys: Sequence[str]) -> Families:
    """Return some families.

    Args:
        families: The families.
        keys: The keys of the families to keep, as strings.

    Returns:
        The families whose keys are given.
    """
    return Families(
        {key: family for key, family in families.items() if str(key) in keys},
        families.along,
        families.ignoring,
        families.ungrouped,
    )


def to_python(
    archive: Mapping[str, Any], query: str, ignored: Sequence[str], call: str = ""
) -> str:
    """Return the Python code computing what the dashboard shows.

    Args:
        archive: The archive settings passed to ``open_model_results``;
            the empty ones are left out.
        query: The query selecting the results.
        ignored: The names of the ignored inputs.
        call: The call to a method of the collection, e.g. ``"duplicates()"``.

    Returns:
        The code.
    """
    arguments = ", ".join(
        f"{name}={value!r}" for name, value in archive.items() if value
    )
    code = f"open_model_results({arguments})"
    if query:
        code += f".filter({query!r})"
    if ignored:
        code += f".ignoring({', '.join(repr(name) for name in ignored)})"
    if call:
        code += f".{call}"
    return f"from vimseo.api import open_model_results\n\n{code}"
