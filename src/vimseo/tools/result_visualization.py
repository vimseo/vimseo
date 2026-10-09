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

"""The helpers to visualize a tool result: figures and tables.

A tool result (:class:`.BaseResult`) is visualized with :meth:`.BaseResult.visualize`,
which returns figures, and :meth:`.BaseResult.tabulate`, which returns the numerical
values as tables. This module gathers what these methods share: the settings of the
visualization, the saving and showing of the figures, and the conversion of the fields
of a result to tables.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from collections.abc import Mapping
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any

from numpy import atleast_1d
from numpy import generic
from numpy import ndarray
from pandas import DataFrame

from vimseo.tools.base_settings import BaseSettings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from matplotlib.figure import Figure as MatplotlibFigure
    from plotly.graph_objs import Figure as PlotlyFigure

    from vimseo.tools.post_tools.base_plot import Plotter

    Figure = MatplotlibFigure | PlotlyFigure

LOGGER = logging.getLogger(__name__)

KEY_SEPARATOR = "_"
"""The separator joining the keys of nested figures into a single key."""

_MAX_TEXT_LENGTH = 200
"""The maximum length of the text representing a value which is not a number."""


class BaseVisualizationSettings(BaseSettings):
    """The settings of the visualization of a tool result.

    The settings of a result class derive from this class. Each field must have a
    default value, meaning *all* when it selects variables, so that a result can be
    visualized without knowing the tool which produced it. The fields must be flat:
    numbers, strings, booleans, enumerations or tuples of strings.
    """


def flatten_figures(
    figures: Mapping[str, Figure | Mapping], prefix: str = ""
) -> dict[str, Figure]:
    """Flatten nested mappings of figures into a mapping of figures.

    Args:
        figures: The figures, possibly nested in mappings.
        prefix: The prefix of the keys.

    Returns:
        The figures, whose keys join the nested keys with :data:`KEY_SEPARATOR`.
    """
    flat_figures = {}
    for key, value in figures.items():
        full_key = f"{prefix}{KEY_SEPARATOR}{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flat_figures.update(flatten_figures(value, full_key))
        elif value is not None:
            flat_figures[full_key] = value
    return flat_figures


def get_file_stem(key: str) -> str:
    """Return a file name stem from the key of a figure or a table.

    Args:
        key: The key of the figure or table.

    Returns:
        The key without the characters which are invalid in a file name.
    """
    return re.sub(r"[^\w\-.\[\]]+", "-", key).strip("-")


def is_matplotlib_figure(figure: Any) -> bool:
    """Whether a figure is a matplotlib figure.

    Args:
        figure: The figure.
    """
    return hasattr(figure, "savefig")


def save_figures(
    figures: Mapping[str, Figure],
    directory_path: str | Path,
    file_format: str = "html",
) -> list[Path]:
    """Save figures in a directory, in a file named after the key of each figure.

    Args:
        figures: The figures.
        directory_path: The path to the directory, created if it does not exist.
        file_format: The format of the plotly figures, ``"html"`` or an image format
            (requires the ``kaleido`` package). The matplotlib figures are saved in
            ``"png"`` when the format is ``"html"``.

    Returns:
        The paths to the saved files.
    """
    directory_path = Path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)
    paths = []
    for key, figure in figures.items():
        stem = get_file_stem(key)
        if is_matplotlib_figure(figure):
            extension = "png" if file_format == "html" else file_format
            path = directory_path / f"{stem}.{extension}"
            figure.savefig(path)
        else:
            path = directory_path / f"{stem}.{file_format}"
            if file_format == "html":
                figure.write_html(path)
            else:
                figure.write_image(path)
        paths.append(path)
    return paths


def show_figures(figures: Mapping[str, Figure]) -> None:
    """Show figures.

    Args:
        figures: The figures.
    """
    has_matplotlib_figure = False
    for figure in figures.values():
        if is_matplotlib_figure(figure):
            has_matplotlib_figure = True
        else:
            figure.show()

    if has_matplotlib_figure:
        import matplotlib.pyplot as plt

        plt.show()


def create_figure(plotter_class: type[Plotter], *args: Any, **options: Any) -> Figure:
    """Create the figure of a plotter, without side effect.

    A :class:`.Plotter` is a tool: its execution creates a working directory and is
    archived as a tool run. Here, the plotter works in a temporary directory, its
    execution is not archived, and it neither saves nor shows its figure.

    Args:
        plotter_class: The class of the plotter.
        *args: The positional arguments of :meth:`.Plotter.execute`.
        **options: The options of :meth:`.Plotter.execute`.

    Returns:
        The figure.
    """
    with TemporaryDirectory() as directory_path:
        plotter = plotter_class(
            working_directory=directory_path, archive_manager="none"
        )
        return plotter.execute(*args, save=False, show=False, **options).figure


def to_cell(value: Any) -> Any:
    """Convert a value to the content of a table cell.

    Args:
        value: The value.

    Returns:
        A number, a boolean or a string, or ``None`` for ``None``.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, generic):
        return value.item()
    if isinstance(value, ndarray) and value.size == 1:
        return value.item()
    if hasattr(value, "value") and isinstance(value.value, (int, float, str)):
        # An enumeration.
        return value.value
    from vimseo.utilities.ot_distribution_io import is_ot_distribution

    if is_ot_distribution(value):
        # str() is the short form of an OpenTURNS object, e.g. Normal(mu = 0, ...).
        text = str(value)
        return (
            text
            if len(text) <= _MAX_TEXT_LENGTH
            else f"{text[: _MAX_TEXT_LENGTH - 3]}..."
        )
    text = repr(value.tolist() if isinstance(value, ndarray) else value)
    if len(text) > _MAX_TEXT_LENGTH:
        return f"{text[: _MAX_TEXT_LENGTH - 3]}..."
    return text


def is_scalar(value: Any) -> bool:
    """Whether a value is a scalar, that is a number, a boolean or a string.

    Args:
        value: The value.
    """
    return isinstance(value, (bool, int, float, str, generic)) or (
        isinstance(value, ndarray) and value.size == 1
    )


def mapping_to_dataframe(mapping: Mapping[str, Any]) -> DataFrame | None:
    """Convert a mapping to a table, when its structure allows it.

    Args:
        mapping: The mapping.

    Returns:
        The table, or ``None`` if the mapping has no tabular structure:

        - ``{name: scalar}`` gives a table with a single column ``value``,
        - ``{column: {row: value}}`` gives a table with these rows and columns,
          where the values which are not scalars are represented by a text,
        - ``{name: 1D array}`` with arrays of the same size gives a table with a column
          per name.
    """
    if not mapping:
        return None

    values = list(mapping.values())
    if all(is_scalar(value) or value is None for value in values):
        return DataFrame(
            {"value": [to_cell(value) for value in values]},
            index=[str(name) for name in mapping],
        )

    if all(isinstance(value, Mapping) for value in values):
        return DataFrame({
            str(column): {str(row): to_cell(cell) for row, cell in value.items()}
            for column, value in mapping.items()
        })

    if all(isinstance(value, ndarray) and value.ndim <= 1 for value in values):
        sizes = {value.size for value in values}
        if len(sizes) == 1:
            return DataFrame({
                str(name): atleast_1d(value) for name, value in mapping.items()
            })

    return None


def value_to_dataframe(value: Any) -> DataFrame | None:
    """Convert a value to a table, when its type allows it.

    Args:
        value: The value.

    Returns:
        The table, or ``None`` if the value cannot be represented by a table.
    """
    from gemseo.datasets.dataset import Dataset

    if isinstance(value, Dataset):
        from vimseo.utilities.datasets import dataset_to_dataframe

        try:
            return dataset_to_dataframe(value)
        except Exception:  # ruff: ignore[blind-except]
            return DataFrame(
                value.to_numpy(),
                index=value.index,
                columns=[
                    f"{name}[{group_name}][{component}]"
                    for group_name, name, component in value.columns
                ],
            )

    if isinstance(value, DataFrame):
        return value

    if isinstance(value, Mapping):
        return mapping_to_dataframe(value)

    if isinstance(value, ndarray) and value.ndim in (1, 2) and value.size > 1:
        return DataFrame(value)

    return None


def fields_to_dataframes(
    result: Any, excluded_names: Iterable[str] = ("metadata",)
) -> dict[str, DataFrame]:
    """Convert the fields of a dataclass to tables.

    The fields which are tables or mappings with a tabular structure give a table
    named after the field. The scalar fields are gathered in a table named
    ``"scalars"``. The other fields are ignored.

    Args:
        result: The dataclass.
        excluded_names: The names of the fields to ignore.

    Returns:
        The tables.
    """
    tables = {}
    scalars = {}
    for field in dataclasses.fields(result):
        if field.name in excluded_names:
            continue
        value = getattr(result, field.name)
        if value is None or (isinstance(value, str) and not value):
            continue
        if is_scalar(value):
            scalars[field.name] = value
            continue
        table = value_to_dataframe(value)
        if table is not None and not table.empty:
            tables[field.name] = table

    if scalars:
        tables["scalars"] = mapping_to_dataframe(scalars)

    return tables


def settings_to_dataframe(settings: Mapping[str, Any]) -> DataFrame | None:
    """Convert the settings of a tool to a table.

    Args:
        settings: The settings of the tool.

    Returns:
        A table with a single column ``value`` and a row per setting,
        or ``None`` if there is no setting.
    """
    if not settings:
        return None
    return DataFrame(
        {"value": [to_cell(value) for value in settings.values()]},
        index=list(settings),
    )


def get_number(value: Any) -> float | None:
    """Return a value as a finite number, if it is one.

    Args:
        value: The value, e.g. a number or an array of size one.

    Returns:
        The number, or ``None`` if the value is not a finite number.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, ndarray):
        if value.size != 1 or value.dtype.kind not in "iuf":
            return None
        value = value.item()
    if isinstance(value, generic):
        value = value.item()
    if isinstance(value, (int, float)) and isfinite(value):
        return float(value)
    return None


def flatten_numbers(mapping: Mapping[str, Any], prefix: str = "") -> dict[str, float]:
    """Flatten the numbers of nested mappings.

    Args:
        mapping: The mappings, e.g. ``{metric: {output: value}}``.
        prefix: The prefix of the keys.

    Returns:
        The finite numbers, whose keys join the nested keys with dots,
        e.g. ``{"metric.output": value}``. An array is flattened with the index of
        its components, e.g. ``"metric.output.0"``.
    """
    numbers = {}
    for key, value in mapping.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            numbers.update(flatten_numbers(value, full_key))
            continue
        number = get_number(value)
        if number is not None:
            numbers[full_key] = number
        elif isinstance(value, ndarray) and value.ndim == 1 and value.size > 1:
            numbers.update({
                f"{full_key}.{i}": number
                for i, component in enumerate(value)
                if (number := get_number(component)) is not None
            })
    return numbers
