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
from typing import ClassVar

from docstring_inheritance import GoogleDocstringInheritanceMeta

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.core.components.library_file import LibraryFile


class SubroutineWrapper(metaclass=GoogleDocstringInheritanceMeta):
    """A wrapper for user subroutines."""

    _library_path: str | Path
    """The absolute path to the library directory, e.g. ``lib_vims``."""

    _SUBROUTINE_PATH: ClassVar[LibraryFile | None] = None
    """The standalone subroutine file."""

    def __init__(self):
        if not self._SUBROUTINE_PATH:
            msg = "A subroutine file must be defined."
            raise ValueError(msg)
