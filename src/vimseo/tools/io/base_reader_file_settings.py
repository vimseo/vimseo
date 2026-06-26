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

from pathlib import Path

from pydantic import Field

from vimseo.tools.base_settings import BaseSettings


class BaseFileReaderSettings(BaseSettings):
    """Settings for a base file reader."""

    file_name: str | Path = Field(
        default="", description="The name of the file to read."
    )
    directory_path: str | Path = Field(
        default="", description="The path to the directory containing the file."
    )
    tool_name: str = Field(
        default="", description="The name of the tool to use for reading the file."
    )


class StreamlitBaseFileReaderSettings(BaseSettings):
    """Streamlit settings for a base file reader."""
