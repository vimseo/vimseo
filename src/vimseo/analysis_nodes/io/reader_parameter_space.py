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

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.io.base_reader_file import BaseReaderFile
from vimseo.analysis_nodes.io.base_reader_file_settings import BaseFileReaderSettings
from vimseo.analysis_nodes.space.space_analysis_node_result import (
    SpaceAnalysisNodeResult,
)
from vimseo.io.space_io import SpaceAnalysisNodeFileIO


class ParameterSpaceReaderFileSettings(BaseFileReaderSettings):
    """The settings of a parameter space reader."""


class ParameterSpaceReader(BaseReaderFile):
    result: SpaceAnalysisNodeResult

    _EXTENSION = ".json"

    _SETTINGS = ParameterSpaceReaderFileSettings

    def __init__(self, **options):
        super().__init__(**options)
        self.result = SpaceAnalysisNodeResult()

    @BaseAnalysisNode._validate
    def execute(
        self,
        settings: ParameterSpaceReaderFileSettings | None = None,
        **options,
    ) -> SpaceAnalysisNodeResult:
        self._validate_base_options()
        self.result.parameter_space = (
            SpaceAnalysisNodeFileIO()
            .read(
                directory_path=options["directory_path"], file_name=options["file_name"]
            )
            .parameter_space
        )
