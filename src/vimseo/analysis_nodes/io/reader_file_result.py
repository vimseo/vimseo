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

from vimseo.analysis_nodes.analysis_nodes_factory import CompositeAnalysisNodesFactory
from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.io.base_reader_file import BaseReaderFile
from vimseo.analysis_nodes.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.analysis_nodes.io.base_reader_file_settings import (
    StreamlitBaseFileReaderSettings,
)

if TYPE_CHECKING:
    from vimseo.analysis_nodes.base_result import BaseResult


class ResultFileReaderAnalysisNode(BaseReaderFile):
    """An analysis node to read analysis node data from a file and return the result."""

    result: BaseResult

    _SETTINGS = BaseFileReaderSettings

    _STREAMLIT_SETTINGS = StreamlitBaseFileReaderSettings

    _EXTENSION = BaseAnalysisNode._RESULT_FORMATS

    def __init__(
        self,
        analysis_node_name: str,
        **options,
    ):
        super().__init__(**options)
        self.result = CompositeAnalysisNodesFactory().create(analysis_node_name).result

    def get_file_extension(self):
        return self._EXTENSION

    @BaseAnalysisNode._validate
    def execute(
        self,
        settings: BaseFileReaderSettings | None = None,
        **options,
    ) -> Any:
        analysis_node = CompositeAnalysisNodesFactory().create(
            options["analysis_node_name"]
        )
        self.result = analysis_node.load_results(options["file_name"])
