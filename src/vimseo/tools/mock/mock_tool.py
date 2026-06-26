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

from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseResult
from vimseo.tools.base_tool import BaseTool


class MockToolResult(BaseResult):
    """A mock result."""

    mock_data = None


class MySettings(BaseSettings):
    foo: str = ""


class MyInputs(BaseInputs):
    bar: str = ""


class MyTool(BaseTool):
    """A mock tool with inputs and settings."""

    _SETTINGS = MySettings
    _INPUTS = MyInputs

    @BaseTool.validate
    def execute(
        self,
        inputs: MyInputs | None = None,
        settings: MySettings | None = None,
        **options,
    ):
        """A mock run."""


class MyToolNoInputs(BaseTool):
    """A mock tool without inputs."""

    _SETTINGS = MySettings

    @BaseTool.validate
    def execute(
        self,
        settings: MySettings | None = None,
        **options,
    ):
        """A mock run."""


class MyCompositeSettings(MySettings):
    composite_foo: str = ""


class MyBaseCompositeTool(BaseCompositeTool):
    """A mock composite tool."""

    _SETTINGS = MyCompositeSettings

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: MyInputs | None = None,
        settings: MyCompositeSettings | None = None,
        **options,
    ):
        """Saves metadata on disk."""

        for tool in self._subtools.values():
            tool.execute(**tool.get_filtered_options(**options))
            tool.result.save_metadata_to_disk(tool.working_directory)

        self.result.save_metadata_to_disk(self.working_directory)
