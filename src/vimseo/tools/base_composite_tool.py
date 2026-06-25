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

import functools
import logging

from pydantic import ConfigDict
from pydantic import Field

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.base_tool import StreamlitToolConstructorSettings
from vimseo.tools.base_tool import ToolConstructorSettings

LOGGER = logging.getLogger(__name__)


class BaseCompositeToolConstructorSettings(ToolConstructorSettings):
    """The options of the BaseCompositeTool constructor."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    subtools: list[BaseTool] = Field(
        default=[], description="The tools used in this tool."
    )


class StreamlitBaseCompositeToolConstructorSettings(StreamlitToolConstructorSettings):
    """The options of the BaseCompositeTool constructor."""

    subtools: list = []  # noqa: RUF012


class BaseCompositeTool(BaseTool):
    """A tool executing other tools."""

    _STREAMLIT_CONSTRUCTOR_OPTIONS = StreamlitBaseCompositeToolConstructorSettings

    def __init__(self, **options):
        options = BaseCompositeToolConstructorSettings(**options).model_dump()
        self._subtools = {tool.name: tool for tool in options.pop("subtools")}
        super().__init__(**options)

    def validate(f):  # noqa: N805
        @functools.wraps(f)
        def decorated(self, *args, **options):
            self._create_working_directory()
            for tool in self._subtools.values():
                tool.working_directory = self.working_directory / tool.name
                tool._create_working_directory()

            options = self._pre_process_options(**options)
            f(self, *args, **options)
            self._set_options_to_results(options)
            return self.result

        return decorated

    def save_results(self, prefix: str = "", file_format: str = "hdf5") -> None:
        super().save_results(prefix, file_format=file_format)
        for tool in self._subtools.values():
            tool.save_results(prefix, file_format=file_format)
