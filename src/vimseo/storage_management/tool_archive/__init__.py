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

"""The archives of the results of the tools."""

from __future__ import annotations

import logging
from pathlib import Path

from vimseo.storage_management import ArchiveManager
from vimseo.storage_management.tool_archive.base_tool_archive import BaseToolArchive
from vimseo.storage_management.tool_archive.base_tool_archive import NullToolArchive
from vimseo.storage_management.tool_archive.directory_tool_archive import (
    DirectoryToolArchive,
)
from vimseo.utilities.optional_dependencies import import_optional

LOGGER = logging.getLogger(__name__)

NO_TOOL_ARCHIVE = "none"
"""The name of the archive manager which disables the archive of the tool results."""


def open_tool_archive(name: str, root_directory: Path | str) -> BaseToolArchive:
    """Open the archive of the results of the tools.

    The tool runs already archived under ``root_directory`` are kept: they can be
    searched and read, and the new tool runs are added to them. The archive is
    created if it does not exist yet.

    The names are the ones of the archive managers of the simulations (see
    :class:`.ArchiveManager`), plus ``"none"`` to disable the archive.

    Args:
        name: The name of the archive manager.
        root_directory: The root directory of the archive.

    Returns:
        The archive.

    Raises:
        ValueError: If ``name`` does not match any archive manager.
    """
    if name.lower() == NO_TOOL_ARCHIVE:
        return NullToolArchive()

    if name == ArchiveManager.Directory:
        return DirectoryToolArchive(Path(root_directory))

    if name == ArchiveManager.Mlflow:
        # mlflow is shipped by the ``mlflow`` extra: it is imported lazily.
        import_optional("mlflow", "mlflow", feature="The MLflow archive of the tools")
        from vimseo.storage_management.tool_archive.mlflow_tool_archive import (
            MlflowToolArchive,
        )

        return MlflowToolArchive(root_directory)

    msg = (
        f"Unknown archive manager for the tool results: {name}. "
        f"Available ones: {sorted([*(m.value for m in ArchiveManager), NO_TOOL_ARCHIVE])}."
    )
    raise ValueError(msg)
