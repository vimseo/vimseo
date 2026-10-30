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
from typing import Any

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_analysis_node import BaseResult
from vimseo.analysis_nodes.base_composite_analysis_node import BaseCompositeAnalysisNode
from vimseo.analysis_nodes.base_settings import BaseInputs
from vimseo.analysis_nodes.base_settings import BaseSettings


@dataclass
class MockAnalysisNodeResult(BaseResult):
    """A mock result."""

    mock_data: Any = None


class MySettings(BaseSettings):
    foo: str = ""


class MyInputs(BaseInputs):
    bar: str = ""


class MyAnalysisNode(BaseAnalysisNode):
    """A mock analysis node with inputs and settings."""

    _SETTINGS = MySettings
    _INPUTS = MyInputs

    @BaseAnalysisNode._validate
    def execute(
        self,
        inputs: MyInputs | None = None,
        settings: MySettings | None = None,
        **options,
    ):
        """A mock run."""


class MyAnalysisNodeNoInputs(BaseAnalysisNode):
    """A mock analysis node without inputs."""

    _SETTINGS = MySettings

    @BaseAnalysisNode._validate
    def execute(
        self,
        settings: MySettings | None = None,
        **options,
    ):
        """A mock run."""


class MyCompositeSettings(MySettings):
    composite_foo: str = ""


class MyBaseCompositeAnalysisNode(BaseCompositeAnalysisNode):
    """A mock composite analysis node."""

    _SETTINGS = MyCompositeSettings

    @BaseCompositeAnalysisNode._validate
    def execute(
        self,
        inputs: MyInputs | None = None,
        settings: MyCompositeSettings | None = None,
        **options,
    ):
        """Saves metadata on disk."""

        for analysis_node in self._sub_analysis_nodes.values():
            analysis_node.execute(**analysis_node.get_filtered_options(**options))
            analysis_node.result.save_metadata_to_disk(analysis_node.working_directory)

        self.result.save_metadata_to_disk(self.working_directory)
