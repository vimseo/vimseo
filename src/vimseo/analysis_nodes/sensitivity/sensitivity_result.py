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

import dataclasses
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.uncertainty.sensitivity.base_sensitivity_analysis import (
    BaseSensitivityAnalysis,
)
from gemseo.utils.string_tools import MultiLineString
from pydantic import Field

from vimseo.analysis_nodes.base_analysis_node import BaseResult
from vimseo.analysis_nodes.result_visualization import BasePlotSettings
from vimseo.analysis_nodes.result_visualization import flatten_numbers
from vimseo.analysis_nodes.sensitivity.indices import indices_to_dataframe
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from pandas import DataFrame

    from vimseo.analysis_nodes.result_visualization import Figure

LOGGER = logging.getLogger(__name__)

_MORRIS_ALGORITHMS = ("Morris", "MorrisAnalysis")
"""The names of the Morris sensitivity analysis."""

_MAIN_INDEX_NAMES = {
    "Morris": "mu_star",
    "MorrisAnalysis": "mu_star",
    "HSIC": "r2_hsic",
    "HSICAnalysis": "r2_hsic",
}
"""The names of the main indices of the sensitivity analyses."""


class SensitivityVisualizationSettings(BasePlotSettings):
    output_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the outputs whose sensitivity indices are shown. "
        "If empty, use all the outputs of the analysis.",
    )
    standardize: bool = Field(
        default=False,
        description="Whether to standardize the sensitivity indices.",
    )


@dataclass
class SensitivityResult(BaseResult):
    """The result of a sensitivity analysis."""

    _PLOT_SETTINGS: ClassVar[type[SensitivityVisualizationSettings]] = (
        SensitivityVisualizationSettings
    )

    analysis: BaseSensitivityAnalysis | None = None
    """The sensitivity analysis."""

    indices: BaseSensitivityAnalysis.SensitivityIndices = field(default=None)
    """The indices of the sensitivity analysis."""

    variable_dimensions: Mapping[str, int] = field(default_factory=dict)

    def get_indices_dataframe(self, index_name: str = "") -> DataFrame:
        """Return sensitivity indices as a table.

        Args:
            index_name: The name of the indices, e.g. ``"mu_star"`` or ``"sigma"``
                for a Morris analysis, ``"hsic"`` or ``"r2_hsic"`` for a HSIC one.
                If empty, use the main indices of the analysis,
                i.e. ``"mu_star"`` for Morris and ``"r2_hsic"`` for HSIC.

        Returns:
            The indices, with a row per input component
            and a column per non-constant output component.
        """
        if not index_name:
            index_name = _MAIN_INDEX_NAMES[self.metadata.settings["sensitivity_algo"]]

        indices = self.indices
        indices = (
            indices[index_name]
            if isinstance(indices, Mapping)
            else getattr(indices, index_name)
        )
        return indices_to_dataframe(indices)

    def __str__(self):
        text = MultiLineString()
        text.add("Results of a sensitivity analysis.")
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        text.add("")
        text.add("Input variables by decreasing order of influence:")
        text.indent()
        for name in self.analysis.default_output_names:
            text.add(f"For output {name}: {self.analysis.sort_input_variables(name)}.")
        text.dedent()
        text.add("Sensitivity indices:")
        text.indent()
        for index_name in self.indices.__annotations__:
            text.add(f"Index {index_name}")
            text.indent()
            for name in self.analysis.default_output_names:
                text.add(f"{name}: {getattr(self.indices, index_name)[name]}")
            text.dedent()
        return str(text)

    def get_plot_choices(self) -> dict[str, list[str]]:
        if self.analysis is None:
            return {}
        return {"output_names": list(self.analysis.default_output_names)}

    def _create_figures(
        self, settings: SensitivityVisualizationSettings
    ) -> dict[str, Figure]:
        if (
            self.analysis is None
            or self.metadata.settings.get("sensitivity_algo") not in _MORRIS_ALGORITHMS
        ):
            return {}

        output_names = settings.output_names or self.analysis.default_output_names
        figures = {
            "radar_plot": self.analysis.plot_radar(
                outputs=output_names,
                standardize=settings.standardize,
                show=False,
                save=False,
            ).figures[0],
            "bar_plot": self.analysis.plot_bar(
                outputs=output_names,
                standardize=settings.standardize,
                show=False,
                save=False,
                file_format="html",
            ).figures[0],
        }

        final_names = []
        for name in output_names:
            if self.variable_dimensions[name] > 1:
                final_names.extend(
                    (name, i) for i in range(self.variable_dimensions[name])
                )
            else:
                final_names.append(name)

        # gemseo's standard mu*/sigma scatter plot keys its indices by
        # whole input-variable name and assumes one scalar value per name,
        # so it cannot mix a vector-valued input (several components) with
        # a scalar one on the same chart; restrict it to scalar inputs
        # (already fully covered by the radar and bar plots above).
        scalar_input_names = [
            name
            for name in self.analysis.input_names
            if self.variable_dimensions[name] == 1
        ]
        for name in final_names:
            key = name if isinstance(name, str) else f"{name[0]}[{name[1]}]"
            figures[f"standard_plot_{key}"] = self.analysis.plot(
                output=name,
                input_names=scalar_input_names,
                show=False,
                save=False,
            )
        return figures

    def _create_tables(self) -> dict[str, DataFrame]:
        tables = {}
        if self.indices is None:
            return tables

        if isinstance(self.indices, Mapping):
            index_names = list(self.indices)
        elif dataclasses.is_dataclass(self.indices):
            index_names = [field.name for field in dataclasses.fields(self.indices)]
        else:
            index_names = list(self.indices.__annotations__)
        for index_name in index_names:
            table = _to_dataframe(
                self.indices[index_name]
                if isinstance(self.indices, Mapping)
                else getattr(self.indices, index_name, None)
            )
            if table is not None:
                tables[f"indices_{index_name}"] = table
        return tables

    def get_key_values(self) -> dict[str, float]:
        # The indices by kind, output and input, e.g. "mu_star.y.x1".
        return flatten_numbers({
            name.removeprefix("indices_"): table.to_dict()
            for name, table in self._create_tables().items()
        })


def _to_dataframe(indices) -> DataFrame | None:
    """Convert sensitivity indices of a kind to a table, see
    :func:`.indices_to_dataframe`.

    Returns:
        The table, or ``None`` if the indices do not have the structure
        ``{output_name: [{input_name: values}]}`` or are empty.
    """
    if not isinstance(indices, Mapping) or not indices:
        return None
    try:
        table = indices_to_dataframe(indices)
    except (TypeError, ValueError, AttributeError):
        return None
    return None if table.empty else table
