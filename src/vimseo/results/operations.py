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

"""The functions behind the verbs of the collections of results.

They work on the table of the summaries of the results, one row per result, whose
columns are the metadata, ``inputs.{name}`` and ``outputs.{name}``. They return new
objects and never change their arguments nor the archive.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING
from typing import Any

from pandas import DataFrame

from vimseo.results.query import apply_query

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

INPUT_PREFIX = "inputs."
"""The prefix of the columns of the inputs."""

OUTPUT_PREFIX = "outputs."
"""The prefix of the columns of the outputs."""

FINISHED = "FINISHED"
"""The status of a successful run."""


def get_input_columns(summaries: DataFrame, ignored: Iterable[str] = ()) -> list[str]:
    """Return the columns of the inputs, except the ignored ones.

    Args:
        summaries: The summaries.
        ignored: The names of the inputs to ignore.
    """
    ignored = {f"{INPUT_PREFIX}{name}" for name in ignored}
    return [
        column
        for column in summaries.columns
        if column.startswith(INPUT_PREFIX) and column not in ignored
    ]


def filter_summaries(
    summaries: DataFrame,
    query: str = "",
    failed: bool | None = None,
    **metadata: Any,
) -> DataFrame:
    """Select the summaries.

    Args:
        summaries: The summaries.
        query: A query, see :mod:`.query`.
        failed: Whether to keep only the failed runs (``True``), only the others
            (``False``), or both (``None``). A run is failed when its status is not
            ``FINISHED`` or its ``error_code`` is positive; ``-1`` means that the
            model reports no error code.
        **metadata: Values of metadata which the runs must have, e.g.
            ``model_name="BendingTestAnalytical"``.

    Returns:
        The selected summaries.

    Raises:
        KeyError: If a metadata is not a column of the summaries.
    """
    selected = summaries
    for name, value in metadata.items():
        if name not in selected.columns:
            if selected.empty:
                continue
            msg = f"Unknown metadata {name}; the columns are {list(selected.columns)}."
            raise KeyError(msg)
        selected = selected[selected[name] == value]
    if failed is not None and not selected.empty:
        is_failed = selected["status"] != FINISHED
        if "error_code" in selected.columns:
            is_failed |= selected["error_code"].fillna(0).astype(int) > 0
        selected = selected[is_failed == failed]
    return apply_query(selected, query)


def get_varying_inputs(summaries: DataFrame, ignored: Iterable[str] = ()) -> DataFrame:
    """Return the inputs taking several values.

    Args:
        summaries: The summaries.
        ignored: The names of the inputs to ignore.

    Returns:
        One row per varying input, indexed by its name, with the number of its values
        and the sorted values.
    """
    rows = {}
    for column in get_input_columns(summaries, ignored):
        values = summaries[column].dropna().unique().tolist()
        if len(values) > 1:
            rows[column[len(INPUT_PREFIX) :]] = {
                "n_values": len(values),
                "values": sorted(values, key=_sort_key),
            }
    return DataFrame.from_dict(
        rows, orient="index", columns=["n_values", "values"]
    ).rename_axis("input")


def _sort_key(value: Any) -> tuple[int, Any]:
    """Return a key sorting numbers before strings."""
    return (0, value) if isinstance(value, (int, float)) else (1, str(value))


def find_duplicates(summaries: DataFrame, ignored: Iterable[str] = ()) -> DataFrame:
    """Return the groups of runs with the same inputs.

    Nothing is deleted: the duplicates are only reported.

    Args:
        summaries: The summaries.
        ignored: The names of the inputs to ignore.

    Returns:
        The runs which have a duplicate, with a column ``group`` numbering the groups.
    """
    columns = get_input_columns(summaries, ignored)
    if summaries.empty or not columns:
        return DataFrame(columns=["group", *summaries.columns])
    keys = summaries[columns].astype(str).agg("|".join, axis=1)
    duplicated = summaries[keys.duplicated(keep=False)]
    groups = {
        key: index for index, key in enumerate(dict.fromkeys(keys[duplicated.index]))
    }
    duplicated = duplicated.assign(group=keys[duplicated.index].map(groups))
    return duplicated[["group", *summaries.columns]].sort_values("group", kind="stable")


def to_dataframe(
    summaries: DataFrame, id_column: str, variable_names: Iterable[str] = ()
) -> DataFrame:
    """Return the table of the runs, one row per run, indexed by their identifiers.

    Args:
        summaries: The summaries.
        id_column: The column of the identifiers.
        variable_names: The names of the inputs and outputs, without prefix.
            If empty, all the columns.

    Returns:
        The table, whose columns are the names of the variables, without prefix
        unless an input and an output have the same name.
    """
    variable_names = list(variable_names)
    if not variable_names:
        table = summaries
    else:
        columns = []
        for name in variable_names:
            for column in (f"{INPUT_PREFIX}{name}", f"{OUTPUT_PREFIX}{name}", name):
                if column in summaries.columns:
                    columns.append(column)
                    break
            else:
                msg = f"Unknown variable {name}."
                raise KeyError(msg)
        table = (
            summaries[[id_column, *columns]]
            if id_column not in columns
            else (summaries[columns])
        )
    # A column keeps its prefix when its name would collide with another column, e.g.
    # a setting and a key value of an analysis node, both named n_samples.
    stripped = Counter(
        column.split(".", 1)[1]
        for column in table.columns
        if column.startswith((INPUT_PREFIX, OUTPUT_PREFIX))
    )
    renamed = {
        column: name
        for column in table.columns
        if column.startswith((INPUT_PREFIX, OUTPUT_PREFIX))
        and stripped[name := column.split(".", 1)[1]] == 1
        and name not in table.columns
    }
    return table.rename(columns=renamed).set_index(id_column)


def to_dataset(summaries: DataFrame, variable_names: Iterable[str] = ()):
    """Return the numerical inputs and outputs as an ``IODataset``.

    Args:
        summaries: The summaries.
        variable_names: The names of the inputs and outputs, without prefix.
            If empty, all the numerical ones.

    Returns:
        The dataset, one sample per run, with the groups of the inputs and outputs.
    """
    from gemseo.datasets.io_dataset import IODataset

    variable_names = set(variable_names)
    dataset = IODataset()
    for prefix, group in (
        (INPUT_PREFIX, IODataset.INPUT_GROUP),
        (OUTPUT_PREFIX, IODataset.OUTPUT_GROUP),
    ):
        for column in summaries.columns:
            name = column[len(prefix) :]
            if not column.startswith(prefix) or (
                variable_names and name not in variable_names
            ):
                continue
            values = summaries[column]
            if values.map(lambda value: isinstance(value, (int, float))).all():
                dataset.add_variable(
                    name, values.to_numpy(dtype=float)[:, None], group_name=group
                )
    return dataset


def group_by_variation(
    summaries: DataFrame, along: str, ignored: Iterable[str] = ()
) -> tuple[dict[tuple[tuple[str, Any], ...], list[Any]], list[Any]]:
    """Group the runs which differ by one input only.

    Args:
        summaries: The summaries.
        along: The name of the input varying in a family.
        ignored: The names of the inputs to ignore.

    Returns:
        The index labels of the rows of each family, sorted by the varying input and
        bound to the values of the other varying inputs, and the labels of the rows
        alone in their group.

    Raises:
        KeyError: If ``along`` is not an input.
    """
    column = f"{INPUT_PREFIX}{along}"
    if column not in summaries.columns:
        msg = f"Unknown input {along}."
        raise KeyError(msg)
    other_columns = [
        name for name in get_varying_inputs(summaries, ignored).index if name != along
    ]
    families = {}
    ungrouped = []
    groups = (
        summaries.groupby(
            [f"{INPUT_PREFIX}{name}" for name in other_columns],
            dropna=False,
            sort=True,
        )
        if other_columns
        else [((), summaries)]
    )
    for key, rows in groups:
        key = key if isinstance(key, tuple) else (key,)
        if rows[column].nunique(dropna=True) > 1:
            rows = rows.sort_values(column, kind="stable")
            families[tuple(zip(other_columns, key, strict=True))] = list(rows.index)
        else:
            ungrouped.extend(rows.index)
    return families, ungrouped


def get_labels(
    summaries: DataFrame, id_column: str, ignored: Iterable[str]
) -> list[str]:
    """Return a label per run, from its varying inputs, else its identifier.

    Args:
        summaries: The summaries.
        id_column: The column of the identifiers.
        ignored: The names of the inputs to ignore.
    """
    varying = list(get_varying_inputs(summaries, ignored).index)
    if not varying:
        return list(summaries[id_column])
    return [
        ", ".join(
            f"{name} = {_format(row[f'{INPUT_PREFIX}{name}'])}" for name in varying
        )
        for _, row in summaries.iterrows()
    ]


def _format(value: Any) -> str:
    """Return a short text of a value."""
    return f"{value:g}" if isinstance(value, float) else str(value)


def get_scalars(row: Mapping[str, Any]) -> dict[str, float]:
    """Return the numerical outputs of a row of summaries, without prefix."""
    return {
        name[len(OUTPUT_PREFIX) :]: value
        for name, value in row.items()
        if name.startswith(OUTPUT_PREFIX)
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    }
