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

# Copyright (c) 2022 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Jorge CAMACHO-CASERO, Ludovic BARRIERE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.algos.parameter_space import ParameterSpace
from pandas import DataFrame
from pydantic import Field
from pydantic import PositiveInt

from vimseo.tools.base_tool import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import to_cell

if TYPE_CHECKING:
    from vimseo.tools.result_visualization import Figure


class SpaceToolVisualizationSettings(BaseVisualizationSettings):
    n_samples: PositiveInt = Field(
        default=10,
        description="The number of samples used to represent the parameter space.",
    )


@dataclass
class SpaceToolResult(BaseResult):
    """The result of the :class:`~.SpaceTool`."""

    _VISUALIZATION_SETTINGS: ClassVar[type[SpaceToolVisualizationSettings]] = (
        SpaceToolVisualizationSettings
    )

    parameter_space: ParameterSpace | None = None
    """The parameter space."""

    def _create_figures(
        self, settings: SpaceToolVisualizationSettings
    ) -> dict[str, Figure]:
        if self.parameter_space is None or not self.parameter_space.variable_names:
            return {}

        from gemseo.datasets.dataset import Dataset
        from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix

        dataset = Dataset.from_array(
            data=self.parameter_space.compute_samples(settings.n_samples),
            variable_names=self.parameter_space.uncertain_variables,
        )
        figures = ScatterMatrix(dataset).execute(save=False, show=False)
        return {"scatter_matrix": figures[0]}

    def _create_tables(self) -> dict[str, DataFrame]:
        if self.parameter_space is None:
            return {}

        rows = {}
        for name in self.parameter_space.variable_names:
            row = {
                "size": self.parameter_space.get_size(name),
                "lower_bound": to_cell(self.parameter_space.get_lower_bound(name)),
                "upper_bound": to_cell(self.parameter_space.get_upper_bound(name)),
            }
            if name in self.parameter_space.distributions:
                row["distribution"] = to_cell(self.parameter_space.distributions[name])
            rows[name] = row
        return {"parameter_space": DataFrame.from_dict(rows, orient="index")}
