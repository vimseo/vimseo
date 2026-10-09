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

"""A command line to visualize tool results.

The figures and the tables of each tool result are written in a directory::

    visualize_tool_result --uri path/to/SensitivityTool_result.hdf5
    visualize_tool_result --uri tool-run:1b2c... --archive-root my_archive
    visualize_tool_result --uri runs:/9f8e... --archive-root my_mlflow_archive
    visualize_tool_result --uri result.hdf5 --option output_names='["y1"]'
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from pydantic import ValidationError

from vimseo.storage_management.tool_archive.uri import load_tool_result
from vimseo.tools.result_visualization import get_file_stem
from vimseo.tools.result_visualization import save_figures
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vimseo.tools.base_result import BaseResult

LOGGER = logging.getLogger(__name__)

FIGURES_DIRECTORY_NAME = "figures"
"""The name of the directory of the figures of a tool result."""

TABLES_DIRECTORY_NAME = "tables"
"""The name of the directory of the tables of a tool result."""

METADATA_FILE_NAME = "metadata.json"
"""The name of the file of the metadata of a tool result."""


def parse_options(options: Sequence[str]) -> dict[str, Any]:
    """Parse the settings of the visualization passed as ``key=value``.

    Args:
        options: The settings as ``key=value``. A value is read as JSON,
            else as a string.

    Returns:
        The settings.

    Raises:
        ValueError: If a setting is not ``key=value``.
    """
    parsed_options = {}
    for option in options:
        name, separator, value = option.partition("=")
        if not separator or not name:
            msg = f"The option '{option}' is not formatted as key=value."
            raise ValueError(msg)
        try:
            parsed_options[name] = json.loads(value)
        except json.JSONDecodeError:
            parsed_options[name] = value
    return parsed_options


def get_output_directory_name(result: BaseResult, uri: str) -> str:
    """Return the name of the directory of the outputs of a tool result.

    Args:
        result: The tool result.
        uri: The URI of the tool result.

    Returns:
        The class of the result, followed by the identifier of its tool run if any,
        else by the name of the file or directory of the URI.
    """
    identifier = getattr(result.metadata, "tool_run_id", "") or Path(uri).stem
    return get_file_stem(f"{type(result).__name__}_{identifier}")


def _to_json_value(value: Any) -> Any:
    """Convert a value that :mod:`json` cannot encode, without ever failing."""
    try:
        return EnhancedJSONEncoder().default(value)
    except TypeError:
        return repr(value)


def write_visualization(
    result: BaseResult,
    directory_path: str | Path,
    file_format: str = "html",
    figures: bool = True,
    tables: bool = True,
    **options: Any,
) -> list[Path]:
    """Write the figures, the tables and the metadata of a tool result.

    Args:
        result: The tool result.
        directory_path: The directory where the files are written.
        file_format: The format of the plotly figures.
        figures: Whether to write the figures.
        tables: Whether to write the tables, in CSV format.
        **options: The settings of the visualization.

    Returns:
        The paths to the written files.
    """
    directory_path = Path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)
    paths = []
    if figures:
        paths.extend(
            save_figures(
                result.visualize(**options),
                directory_path / FIGURES_DIRECTORY_NAME,
                file_format,
            )
        )

    if tables:
        tables_directory = directory_path / TABLES_DIRECTORY_NAME
        tables_directory.mkdir(exist_ok=True)
        for key, table in result.tabulate().items():
            path = tables_directory / f"{get_file_stem(key)}.csv"
            table.to_csv(path)
            paths.append(path)

    path = directory_path / METADATA_FILE_NAME
    path.write_text(
        json.dumps(asdict(result.metadata), indent=2, default=_to_json_value)
    )
    paths.append(path)
    return paths


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visualize_tool_result",
        description="Write the figures and the tables of tool results in a directory.",
    )
    parser.add_argument(
        "--uri",
        action="append",
        required=True,
        help="The URI of a tool result: the path to a result file, the path to the "
        "directory of a tool run in an archive, tool-run:{tool_run_id} or "
        "runs:/{mlflow_run_id}. "
        "Can be repeated.",
    )
    parser.add_argument(
        "--archive-root",
        default="",
        help="The root directory of the archive of the tool results, "
        "used by tool-run:{tool_run_id} and runs:/{mlflow_run_id}. "
        "By default, the one of the configuration.",
    )
    parser.add_argument(
        "--archive-manager",
        default="",
        choices=["", "DirectoryArchive", "MlflowArchive"],
        help="The manager of the archive used by tool-run:{tool_run_id}. "
        "By default, it is guessed from the content of the root directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="visualization",
        help="The directory where a directory per tool result is written.",
    )
    parser.add_argument(
        "--format",
        default="html",
        help="The format of the plotly figures: html, or an image format like png "
        "(requires kaleido). The matplotlib figures are written in png for html.",
    )
    parser.add_argument(
        "--option",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="A setting of the visualization, the value being read as JSON, "
        "e.g. output_names='[\"y1\"]'. Can be repeated. "
        "See --list-options for the available settings.",
    )
    parser.add_argument(
        "--list-options",
        action="store_true",
        help="Print the settings of the visualization of each tool result and exit.",
    )
    parser.add_argument(
        "--no-figures", action="store_true", help="Do not write the figures."
    )
    parser.add_argument(
        "--no-tables", action="store_true", help="Do not write the tables."
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Visualize tool results from the command line.

    Args:
        argv: The arguments of the command line. If ``None``, use ``sys.argv``.

    Returns:
        The exit code.
    """
    parser = _create_parser()
    args = parser.parse_args(argv)
    try:
        options = parse_options(args.option)
    except ValueError as error:
        parser.error(str(error))

    for uri in args.uri:
        result = load_tool_result(uri, args.archive_root, args.archive_manager)
        if args.list_options:
            print(f"{uri} ({type(result).__name__}):")
            print(
                json.dumps(result._VISUALIZATION_SETTINGS.model_json_schema(), indent=2)
            )
            continue

        directory_path = Path(args.output_dir) / get_output_directory_name(result, uri)
        try:
            paths = write_visualization(
                result,
                directory_path,
                file_format=args.format,
                figures=not args.no_figures,
                tables=not args.no_tables,
                **options,
            )
        except ValidationError as error:
            print(
                f"Invalid settings of the visualization of {uri}:\n{error}",
                file=sys.stderr,
            )
            return 2

        print(f"{uri}: {len(paths)} files written in {directory_path}")
        for path in paths:
            print(f"  {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
