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

"""Load a tool result from a URI.

A tool result is identified by one of these URIs:

- the path to a result file, ``path/to/{tool_name}_result.hdf5``,
- the path to the directory of a tool run in a :class:`.DirectoryToolArchive`,
  ``{root}/tools/{tool_name}/{tool_run_id}``,
- ``tool-run:{tool_run_id}``, a tool run in an archive of the tool results, whose
  root directory and manager are given separately,
- ``runs:/{run_id}``, the MLflow run of a tool run in an :class:`.MlflowToolArchive`.

The schemes are resolved by functions registered in :data:`URI_RESOLVERS`, so that
new archives can be plugged in.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from vimseo.storage_management.tool_archive.directory_tool_archive import (
    DirectoryToolArchive,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from vimseo.tools.base_result import BaseResult

TOOL_RUN_SCHEME = "tool-run"
"""The scheme of a tool run in the archive of the configuration."""

MLFLOW_RUN_SCHEME = "runs"
"""The scheme of a run in MLflow."""

_SCHEME_PATTERN = re.compile(r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]+):(?P<path>.*)$")
"""The pattern of a URI with a scheme.

A scheme has at least two characters, so that a Windows drive letter is a path.
"""


def get_default_archive_root() -> str | Path:
    """Return the root directory of the archive of the tool results by default.

    It is the one used by the tools: the ``local_uri`` of the database of the
    configuration, else ``default_archive/``.
    """
    from vimseo.config.global_configuration import _configuration as config
    from vimseo.storage_management.archive_settings import DEFAULT_ARCHIVE_ROOT

    return config.database.local_uri or DEFAULT_ARCHIVE_ROOT


def get_default_archive_manager() -> str:
    """Return the archive manager of the tool results to read from by default.

    It is the one used by the tools: the ``tool_archive_manager`` of the
    configuration, else its ``run_archive_manager``. When the archive of the tool
    results is disabled (``none``), it is the ``run_archive_manager``: disabling the
    archive of the new tool runs does not prevent from reading the former ones.
    """
    from vimseo.config.global_configuration import _configuration as config
    from vimseo.storage_management.tool_archive import NO_TOOL_ARCHIVE

    manager = config.tool_archive_manager
    if not manager or manager.lower() == NO_TOOL_ARCHIVE:
        return config.run_archive_manager
    return manager


def guess_archive_manager(archive_root: str | Path) -> str:
    """Return the manager of an archive of the tool results from its content.

    Args:
        archive_root: The root directory of the archive.

    Returns:
        ``"DirectoryArchive"`` if the root directory holds a ``tools`` directory,
        ``"MlflowArchive"`` if it is a local MLflow database, whose default
        experiment is described by ``0/meta.yaml``, else the archive manager of
        the configuration (see :func:`get_default_archive_manager`).
    """
    from vimseo.storage_management import ArchiveManager

    root = Path(archive_root)
    if (root / DirectoryToolArchive.TOOLS_DIRECTORY_NAME).is_dir():
        return ArchiveManager.Directory
    if (root / "0" / "meta.yaml").is_file():
        return ArchiveManager.Mlflow
    return get_default_archive_manager()


def _load_from_tool_run_id(
    tool_run_id: str, archive_root: str | Path, archive_manager: str
) -> BaseResult:
    """Load a tool result from a tool run of an archive.

    Args:
        tool_run_id: The unique identifier of the tool run.
        archive_root: The root directory of the archive.
            If empty, use :func:`get_default_archive_root`.
        archive_manager: The manager of the archive.
            If empty, use :func:`guess_archive_manager`.
    """
    from vimseo.storage_management.tool_archive import open_tool_archive

    archive_root = archive_root or get_default_archive_root()
    archive = open_tool_archive(
        archive_manager or guess_archive_manager(archive_root), archive_root
    )
    return archive.get_tool_result(tool_run_id.strip("/"))


def _load_from_mlflow_run(
    run_id: str, archive_root: str | Path, archive_manager: str
) -> BaseResult:
    """Load a tool result from an MLflow run of an :class:`.MlflowToolArchive`.

    Args:
        run_id: The id of the MLflow run.
        archive_root: The root directory of a local MLflow database.
            If empty, use :func:`get_default_archive_root`.
        archive_manager: Unused, the archive being an MLflow one.
    """
    from vimseo.storage_management import ArchiveManager
    from vimseo.storage_management.tool_archive import open_tool_archive

    archive = open_tool_archive(
        ArchiveManager.Mlflow, archive_root or get_default_archive_root()
    )
    return archive.get_tool_result_of_mlflow_run(run_id.strip("/"))


URI_RESOLVERS: dict[str, Callable[[str, str | Path, str], BaseResult]] = {
    TOOL_RUN_SCHEME: _load_from_tool_run_id,
    MLFLOW_RUN_SCHEME: _load_from_mlflow_run,
}
"""The functions loading a tool result from the path of a URI, the root directory and
the manager of an archive, bound to the scheme of the URI."""


def _load_from_path(path: Path) -> BaseResult:
    """Load a tool result from a result file or the directory of a tool run.

    Args:
        path: The path to the result file or to the directory of the tool run.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    from vimseo.tools.tool_results_factory import load_result_file

    if path.is_file():
        return load_result_file(path)

    if path.is_dir():
        # The directory of a tool run is in the directory of its tool.
        result_path = path / DirectoryToolArchive.get_result_file_name(path.parent.name)
        if result_path.is_file():
            return load_result_file(result_path)
        msg = (
            f"The directory {path} does not contain the result file {result_path.name}."
        )
        raise FileNotFoundError(msg)

    msg = f"No tool result at {path}."
    raise FileNotFoundError(msg)


def load_tool_result(
    uri: str | Path, archive_root: str | Path = "", archive_manager: str = ""
) -> BaseResult:
    """Load a tool result from a URI.

    Args:
        uri: The URI of the tool result, see :mod:`.uri`.
        archive_root: The root directory of the archive of the tool results,
            used by the URIs which only identify a tool run.
            If empty, use :func:`get_default_archive_root`.
        archive_manager: The manager of the archive of the tool results,
            used by ``tool-run:{tool_run_id}``, e.g. ``"MlflowArchive"``.
            If empty, guess it from the content of the root directory
            (see :func:`guess_archive_manager`).

    Returns:
        The tool result.

    Raises:
        ValueError: If the scheme of the URI is not supported.
    """
    if isinstance(uri, Path):
        return _load_from_path(uri)

    match = _SCHEME_PATTERN.match(uri)
    if match is None:
        return _load_from_path(Path(uri))

    scheme = match.group("scheme")
    if scheme not in URI_RESOLVERS:
        msg = (
            f"Unsupported scheme '{scheme}' in the URI {uri}. "
            f"Supported schemes are {sorted(URI_RESOLVERS)}, "
            "or a path to a result file or to the directory of a tool run."
        )
        raise ValueError(msg)

    return URI_RESOLVERS[scheme](match.group("path"), archive_root, archive_manager)
