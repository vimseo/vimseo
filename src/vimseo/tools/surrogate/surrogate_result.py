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
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.disciplines.surrogate import SurrogateDiscipline
from gemseo.mlearning.core.quality.base_ml_algo_quality import BaseMLAlgoQuality
from gemseo.utils.string_tools import MultiLineString
from numpy import ndarray
from pandas import DataFrame
from prettytable import PrettyTable
from pydantic import Field

from vimseo.tools.base_result import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import flatten_numbers
from vimseo.tools.result_visualization import to_cell
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.tools.result_visualization import Figure

QualitiesType = Mapping[str, Mapping[str, Mapping[str, type(BaseMLAlgoQuality)]]]


class SurrogateVisualizationSettings(BaseVisualizationSettings):
    output_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the outputs whose predictions versus observations "
        "are plotted. If empty, use all the outputs of the surrogate model.",
    )


@dataclass
class SurrogateResult(BaseResult):
    """The result of a :class:`~.SurrogateTool`."""

    _VISUALIZATION_SETTINGS: ClassVar[type[SurrogateVisualizationSettings]] = (
        SurrogateVisualizationSettings
    )

    model: SurrogateDiscipline = None
    """The surrogate model."""

    # TODO use Surrogate.name?
    model_name: str = None
    """The name of the surrogate model."""

    qualities: QualitiesType = field(default_factory=dict)
    """The quality of the surrogate model for the selected measures and evaluation
    methods."""

    selection_qualities: Mapping[
        str, Mapping[str, Mapping[str, Mapping[str, ndarray[float]]]]
    ] = field(default_factory=dict)
    """The qualities of the candidate surrogate models for the selected measures and
    evaluation methods."""

    def __str__(self):
        """Returns a table showing the value of quality measures evaluated for the
        (selected) surrogate model. In case several evaluation methods were used, the
        corresponding values are listed.

        Rows of the returned table correspond to quality measures, while columns
        correspond to evaluation methods.

        Returns:
            A table formatted as a string with rows corresponding to quality
            measure and columns corresponding to evaluation methods.

        Raise:
            KeyError: When no surrogate model is available.
        """
        if len(self.qualities.keys()) > 0:
            measures = list(self.qualities.keys())
        else:
            msg = "No surrogate model is available."
            raise ValueError(msg)

        methods = list(self.qualities[measures[0]].keys())

        msg = MultiLineString()
        msg.add(dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder))
        msg.add(f"=========  Surrogate model: {self.model_name} =========")
        msg.add(" ")
        msg.add(f"{self.model.regression_model}")
        msg.add(" ")
        msg.add("----------- Summary of Surrogate Quality ---------------")

        columns = ["Measure", *methods]
        table = PrettyTable(field_names=columns)

        for measure in measures:
            row = [measure] + [self.qualities[measure][meth] for meth in methods]
            table.add_row(row)

        msg.add(table.get_string())
        msg.add("-----------------------------------------------------------")
        if len(list(self.selection_qualities.keys())):
            candidates = list(self.selection_qualities.keys())
            measures = list(self.selection_qualities[candidates[0]].keys())
            methods = list(self.selection_qualities[candidates[0]][measures[0]].keys())
            msg.add("-------- Qualities of all candidate algorithms ----------")

            columns = ["Measure", "Algo", *methods]
            table = PrettyTable(field_names=columns)

            for measure in measures:
                col1 = f"{measure}"
                for algo in candidates:
                    row = [col1, f"{algo}"] + [
                        self.selection_qualities[algo][measure][meth]
                        for meth in methods
                    ]
                    table.add_row(row)
                    col1 = ""
            msg.add(table.get_string())
            msg.add("-----------------------------------------------------------")

        return str(msg)

    def _create_figures(
        self, settings: SurrogateVisualizationSettings
    ) -> dict[str, Figure]:
        if self.model is None:
            return {}

        from gemseo.post.mlearning.ml_regressor_quality_viewer import (
            MLRegressorQualityViewer,
        )

        # TODO activate cross validation mode when available in GEMSEO.
        viewer = MLRegressorQualityViewer(self.model.regression_model)
        return {
            f"surrogate_{self.model.name}_learning_{output_name}": (
                viewer.plot_predictions_vs_observations(
                    output_name, save=False, show=False
                ).figures[0]
            )
            for output_name in settings.output_names or self.model.output_grammar.names
        }

    def _create_tables(self) -> dict[str, DataFrame]:
        tables = {}
        if self.qualities:
            # A row per quality measure and a column per evaluation method.
            tables["qualities"] = DataFrame({
                method: {
                    measure: to_cell(values[method])
                    for measure, values in self.qualities.items()
                }
                for method in next(iter(self.qualities.values()))
            })
        if self.selection_qualities:
            # A row per candidate algorithm and quality measure,
            # and a column per evaluation method.
            rows = {
                (algo, measure): {
                    method: to_cell(value) for method, value in methods.items()
                }
                for algo, measures in self.selection_qualities.items()
                for measure, methods in measures.items()
            }
            tables["selection_qualities"] = DataFrame.from_dict(rows, orient="index")
        return tables

    def get_key_values(self) -> dict[str, float]:
        # The qualities of the selected surrogate model, by measure and method.
        return flatten_numbers(self.qualities)
