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

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.uncertainty.statistics.base_statistics import BaseStatistics
from gemseo.utils.string_tools import MultiLineString
from pandas import DataFrame
from prettytable import PrettyTable
from pydantic import Field

from vimseo.tools.base_result import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import flatten_numbers
from vimseo.tools.result_visualization import mapping_to_dataframe
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.tools.result_visualization import Figure


class StatisticsVisualizationSettings(BaseVisualizationSettings):
    variable_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the variables whose fitting criteria are shown. "
        "If empty, use all the variables of the analysis.",
    )


@dataclass
class StatisticsResult(BaseResult):
    """The result of a statistics analysis."""

    _VISUALIZATION_SETTINGS: ClassVar[type[StatisticsVisualizationSettings]] = (
        StatisticsVisualizationSettings
    )

    analysis: BaseStatistics | None = None
    """The statistics analysis."""

    best_fitting_distributions: dict[str, str] | None = None

    statistics: OrderedDict | DataFrame | None = None
    """The reduced statistics."""

    def __str__(self):
        text = MultiLineString()
        text.add("Results of a Statistics analysis.")
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        variable_names = list(self.analysis.distributions.keys())
        table = PrettyTable(variable_names)
        table.add_row([
            self.analysis.distributions[name].value for name in variable_names
        ])
        text.add("")
        text.add("Best fitting distribution:")
        text.add(table.get_string())

        text.add("")
        text.add("Fitting matrix (goodness-of-fit measures):")
        text.add(self.analysis.get_fitting_matrix())
        text.add("")
        text.add("Statistics indicators:")
        text.add(repr(self.statistics))
        return str(text)

    def _create_figures(
        self, settings: StatisticsVisualizationSettings
    ) -> dict[str, Figure]:
        if not hasattr(self.analysis, "plot_criteria"):
            return {}

        figures = {}
        for name in settings.variable_names or self.analysis.distributions:
            figures[f"criteria_{name}"] = self.analysis.plot_criteria(
                variable=name,
                title="Criteria of statistics.",
                save=False,
                show=False,
                fig_size=(12.0, 6.0),
            )
        return figures

    def _create_tables(self) -> dict[str, DataFrame]:
        tables = {}
        if isinstance(self.statistics, DataFrame):
            tables["statistics"] = self.statistics
        elif self.statistics:
            table = mapping_to_dataframe(self.statistics)
            if table is not None:
                # A row per variable and a column per statistic.
                tables["statistics"] = table

        if self.best_fitting_distributions:
            tables["best_fitting_distributions"] = mapping_to_dataframe(
                self.best_fitting_distributions
            )

        if hasattr(self.analysis, "get_criteria"):
            criteria = {}
            for name in self.analysis.distributions:
                try:
                    values, _ = self.analysis.get_criteria(name)
                except (KeyError, IndexError, TypeError):
                    continue
                criteria[name] = values
            table = mapping_to_dataframe(criteria)
            if table is not None:
                criterion = getattr(self.analysis, "fitting_criterion", "criterion")
                tables[f"fitting_criteria_{criterion}"] = table
        return tables

    def get_key_values(self) -> dict[str, float]:
        if not isinstance(self.statistics, Mapping):
            return {}
        names = {"mean": "mean", "compute_standard_deviation": "standard_deviation"}
        return flatten_numbers({
            name: self.statistics[key]
            for key, name in names.items()
            if key in self.statistics
        })
