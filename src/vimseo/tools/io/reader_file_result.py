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
from typing import Any

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.io.base_reader_file import BaseReaderFile
from vimseo.tools.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.tools.io.base_reader_file_settings import StreamlitBaseFileReaderSettings
from vimseo.tools.tools_factory import AnalysisToolsFactory

if TYPE_CHECKING:
    from vimseo.tools.base_result import BaseResult


class ResultFileReaderTool(BaseReaderFile):
    """A tool to read tool data from a file and return the result."""

    result: BaseResult

    _SETTINGS = BaseFileReaderSettings

    _STREAMLIT_SETTINGS = StreamlitBaseFileReaderSettings

    _EXTENSION = BaseTool._RESULT_FORMATS

    def __init__(
        self,
        tool_name: str,
    ):
        super().__init__()
        self.result = AnalysisToolsFactory().create(tool_name).result

    def get_file_extension(self):
        return self._EXTENSION

    @BaseTool.validate
    def execute(
        self,
        settings: BaseFileReaderSettings | None = None,
        **options,
    ) -> Any:
        tool = AnalysisToolsFactory().create(options["tool_name"])
        self.result = tool.load_results(options["file_name"])
