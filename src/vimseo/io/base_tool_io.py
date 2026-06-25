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

from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from docstring_inheritance import GoogleDocstringInheritanceMeta

from vimseo.core.model_description import ModelDescription
from vimseo.tools.metadata import ToolResultMetadata

if TYPE_CHECKING:
    from pathlib import Path


class BaseToolFileIO(metaclass=GoogleDocstringInheritanceMeta):
    """A base class to handle reading and writing tool results."""

    _EXTENSION: ClassVar[str]

    # TODO by default use save_result/load_result based on pickle format
    @abstractmethod
    def read(self, file_name: str | Path, directory_path: str | Path = "") -> Any:
        """Read a result."""

    @abstractmethod
    def write(
        self,
        data: Any,
        file_base_name: str | Path = "",
        directory_path: str | Path = "",
    ) -> dict:
        """Write a result."""

    @classmethod
    def create_metadata(cls, data):
        metadata = ToolResultMetadata()
        metadata.generic["datetime"] = data["metadata"]["generic"]["datetime"]
        metadata.generic["version"] = data["metadata"]["generic"]["version"]
        metadata.settings = data["metadata"]["settings"]
        metadata.misc = data["metadata"]["misc"]
        metadata.report = data["metadata"]["report"]
        metadata.model = (
            ModelDescription(**data["metadata"]["model"])
            if data["metadata"]["model"] is not None
            else None
        )
        return metadata
