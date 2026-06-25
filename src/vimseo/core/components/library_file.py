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

from dataclasses import dataclass
from typing import TYPE_CHECKING

from docstring_inheritance import GoogleDocstringInheritanceMeta

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class LibraryFile(metaclass=GoogleDocstringInheritanceMeta):
    """A file contained in the library (e.g. lib_vims)."""

    package_name: Path | str = "vimseo"
    """The name of the package containing the library.

    The library naming convention is "lib_{package_name}".
    """

    file_path: Path | str = ""
    """The path to the file relative to the library."""
