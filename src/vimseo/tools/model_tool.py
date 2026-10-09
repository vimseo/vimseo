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

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import array

from vimseo.api import create_model
from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseResult

if TYPE_CHECKING:
    from pathlib import Path

    from plotly.graph_objs import Figure

    from vimseo.tools.result_visualization import BaseVisualizationSettings


class ModelCreationSettings(BaseSettings):
    name: str = ""
    load_case: str = ""
    default_inputs: Mapping[str, list[float]] = {}


@dataclass
class ModelCreationResult(BaseResult):
    """The result of a :class:`.ModelCreationTool`."""

    model: IntegratedModel | None = None
    """The created model."""

    def _create_figures(
        self, settings: BaseVisualizationSettings
    ) -> Mapping[str, Figure]:
        if self.model is None:
            return {}
        return self.model.plot_results(save=False, show=False)


class ModelCreationTool(BaseAnalysisTool):
    """A tool to create a model and set its default values."""

    _SETTINGS = ModelCreationSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )
        self.result = ModelCreationResult()

    @BaseCompositeTool.validate
    def execute(self, settings=ModelCreationSettings, **options) -> ModelCreationResult:
        model = create_model(options["name"], options["load_case"])
        model.default_input_data.update({
            name: array(value) for name, value in options["default_inputs"].items()
        })
        self.result.model = model
