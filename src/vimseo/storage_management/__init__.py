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

from __future__ import annotations

from typing import TYPE_CHECKING

from strenum import StrEnum

from vimseo.storage_management.directory_storage import DirectoryArchive
from vimseo.utilities.optional_dependencies import import_optional

if TYPE_CHECKING:
    from vimseo.storage_management.base_archive_storage import BaseArchiveManager


class ArchiveManager(StrEnum):
    Directory = "DirectoryArchive"
    Mlflow = "MlflowArchive"


def get_archive_class(name: str) -> type[BaseArchiveManager]:
    """Return the archive manager class matching an ``archive_manager`` setting.

    ``MlflowArchive`` is imported lazily: ``mlflow`` is shipped by the ``mlflow``
    extra, and importing it eagerly would make the whole model layer depend on it.

    Args:
        name: The name of the archive manager,
            one of the values of :class:`.ArchiveManager`.

    Returns:
        The archive manager class.

    Raises:
        ImportError: If ``name`` is ``"MlflowArchive"`` and the ``mlflow`` extra
            is not installed.
        ValueError: If ``name`` does not match any archive manager.
    """
    if name == ArchiveManager.Directory:
        return DirectoryArchive

    if name == ArchiveManager.Mlflow:
        import_optional("mlflow", "mlflow", feature="The MlflowArchive backend")
        from vimseo.storage_management.mlflow_storage import MlflowArchive

        return MlflowArchive

    msg = (
        f"Unknown archive manager: {name}. "
        f"Available ones: {sorted(m.value for m in ArchiveManager)}."
    )
    raise ValueError(msg)
