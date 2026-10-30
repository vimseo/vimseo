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
from typing import TYPE_CHECKING

from pydantic import ConfigDict
from pydantic import Field

from vimseo.analysis_nodes.base_analysis_node import AnalysisNodeConstructorSettings
from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_analysis_node import (
    StreamlitAnalysisNodeConstructorSettings,
)

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class BaseCompositeAnalysisNodeConstructorSettings(AnalysisNodeConstructorSettings):
    """The options of the BaseCompositeAnalysisNode constructor."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sub_analysis_nodes: list[BaseAnalysisNode] = Field(
        default=[], description="The analysis nodes used in this analysis node."
    )


class StreamlitBaseCompositeAnalysisNodeConstructorSettings(
    StreamlitAnalysisNodeConstructorSettings
):
    """The options of the BaseCompositeAnalysisNode constructor."""

    sub_analysis_nodes: list = []  # ruff: ignore[mutable-class-default]


class BaseCompositeAnalysisNode(BaseAnalysisNode):
    """An analysis node executing other analysis nodes."""

    _STREAMLIT_CONSTRUCTOR_OPTIONS = (
        StreamlitBaseCompositeAnalysisNodeConstructorSettings
    )

    def __init__(self, **options):
        options = BaseCompositeAnalysisNodeConstructorSettings(**options).model_dump()
        self._sub_analysis_nodes = {
            analysis_node.name: analysis_node
            for analysis_node in options.pop("sub_analysis_nodes")
        }
        super().__init__(**options)
        # The sub-analysis nodes are usually created without archive settings: they archive
        # their results where their parent does.
        for analysis_node in self._sub_analysis_nodes.values():
            analysis_node._inherit_archive_settings(
                self._archive_manager, self._directory_archive_root, self._study_name
            )

    def _inherit_archive_settings(
        self,
        archive_manager: str | None,
        directory_archive_root: str | Path,
        study_name: str = "",
    ) -> None:
        super()._inherit_archive_settings(
            archive_manager, directory_archive_root, study_name
        )
        for analysis_node in self._sub_analysis_nodes.values():
            analysis_node._inherit_archive_settings(
                self._archive_manager, self._directory_archive_root, self._study_name
            )

    def _validate(f):  # ruff: ignore[invalid-first-argument-name-for-method]
        @functools.wraps(f)
        def decorated(self, *args, **options):
            self._create_working_directory()
            for analysis_node in self._sub_analysis_nodes.values():
                analysis_node.working_directory = (
                    self.working_directory / analysis_node.name
                )
                analysis_node._create_working_directory()

            options = self._pre_process_options(**options)
            self._execute_and_archive(f, args, options)
            return self.result

        return decorated

    def save_results(self, prefix: str = "", file_format: str = "hdf5") -> None:
        super().save_results(prefix, file_format=file_format)
        for analysis_node in self._sub_analysis_nodes.values():
            analysis_node.save_results(prefix, file_format=file_format)
