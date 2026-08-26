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

from strenum import StrEnum


def __getattr__(name: str):
    if name == "MlflowArchive":
        from vimseo.storage_management.mlflow_storage import MlflowArchive

        globals()[name] = MlflowArchive
        return MlflowArchive
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


class ArchiveManager(StrEnum):
    Directory = "DirectoryArchive"
    Mlflow = "MlflowArchive"


_ARCHIVE_CLASSES = {
    "DirectoryArchive": "vimseo.storage_management.directory_storage",
    "MlflowArchive": "vimseo.storage_management.mlflow_storage",
}


def _get_archive_class(name: str):
    module_path = _ARCHIVE_CLASSES.get(name)
    if module_path is None:
        msg = f"Unknown archive manager: {name!r}"
        raise ValueError(msg)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, name)
