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

import logging
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import h5py
from gemseo.core.base_factory import BaseFactory

from vimseo.tools.base_result import BaseResult

if TYPE_CHECKING:
    from io import IOBase

LOGGER = logging.getLogger(__name__)


class ToolResultsFactory(BaseFactory):
    """A factory to create tool results."""

    _CLASS = BaseResult
    _PACKAGE_NAMES = ("vimseo.tools",)

    def create(
        self,
        class_name: str,
        **options,
    ) -> BaseResult:
        """Create an analysis tool.

        Args:
            name: The name of the tool result (its class name).
            **options: The options of the tool result .
        """
        return super().create(class_name, **options)


RESULT_FILE_FORMATS = ("hdf5",)
"""The formats of the files of the tool results which can be loaded."""


def _get_result_class(file: h5py.File) -> type[BaseResult]:
    """Return the class of the tool result stored in an HDF5 file.

    Args:
        file: The HDF5 file.
    """
    return ToolResultsFactory().get_class(file.attrs["__class__"])


def load_result_file(path: str | Path) -> BaseResult:
    """Load a tool result from an HDF5 file written by :meth:`.BaseResult.to_hdf5`.

    The class of the result is read from the file.

    Args:
        path: The path to the file.

    Returns:
        The tool result.

    Raises:
        ValueError: If the file format is not supported.
    """
    path = Path(path)
    if path.suffix[1:] not in RESULT_FILE_FORMATS:
        msg = (
            f"Unsupported file format {path.suffix} for a tool result. "
            f"Supported formats are {RESULT_FILE_FORMATS}."
        )
        raise ValueError(msg)

    with h5py.File(path, "r") as file:
        return _get_result_class(file)._from_hdf5_file(file)


def load_result_buffer(buffer: IOBase | bytes) -> BaseResult:
    """Load a tool result from the content of an HDF5 file.

    It is typically used to load a file uploaded in a dashboard.

    Args:
        buffer: The content of the HDF5 file, as a file-like object or bytes.

    Returns:
        The tool result.
    """
    if isinstance(buffer, bytes):
        buffer = BytesIO(buffer)
    else:
        buffer.seek(0)
        buffer = BytesIO(buffer.read())
    with h5py.File(buffer, "r") as file:
        return _get_result_class(file)._from_hdf5_file(file)
