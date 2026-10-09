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
from numpy import atleast_1d
from pandas import DataFrame
from pydantic import Field

from vimseo.tools.base_tool import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import flatten_numbers
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.tools.result_visualization import Figure

LOGGER = logging.getLogger(__name__)

_MORRIS_ALGORITHMS = ("Morris", "MorrisAnalysis")
"""The names of the Morris sensitivity analysis."""


class SensitivityVisualizationSettings(BaseVisualizationSettings):
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

    _VISUALIZATION_SETTINGS: ClassVar[type[SensitivityVisualizationSettings]] = (
        SensitivityVisualizationSettings
    )

    analysis: BaseSensitivityAnalysis | None = None
    """The sensitivity analysis."""

    indices: BaseSensitivityAnalysis.SensitivityIndices = field(default=None)
    """The indices of the sensitivity analysis."""

    variable_dimensions: Mapping[str, int] = field(default_factory=dict)

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

    def _create_figures(
        self, settings: SensitivityVisualizationSettings
    ) -> dict[str, Figure]:
        if (
            self.analysis is None
            or self.metadata.settings.get("sensitivity_algo") not in _MORRIS_ALGORITHMS
        ):
            return {}

        output_names = settings.output_names or self.metadata.settings["output_names"]
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

        index_names = (
            [field.name for field in dataclasses.fields(self.indices)]
            if dataclasses.is_dataclass(self.indices)
            else list(self.indices.__annotations__)
        )
        for index_name in index_names:
            table = _indices_to_dataframe(getattr(self.indices, index_name, None))
            if table is not None:
                tables[f"indices_{index_name}"] = table
        return tables

    def get_key_values(self) -> dict[str, float]:
        # The indices by kind, output and input, e.g. "mu_star.y.x1".
        return flatten_numbers({
            name.removeprefix("indices_"): table.to_dict()
            for name, table in self._create_tables().items()
        })


def _indices_to_dataframe(indices) -> DataFrame | None:
    """Convert sensitivity indices to a table.

    Args:
        indices: The sensitivity indices of a kind, as
            ``{output_name: [{input_name: array} for each output component]}``.

    Returns:
        The table, with a row per input component and a column per output component,
        or ``None`` if the indices do not have this structure.
    """
    if not isinstance(indices, Mapping) or not indices:
        return None

    columns = {}
    try:
        for output_name, components in indices.items():
            for i, component in enumerate(components):
                if component is None:
                    # A constant output component.
                    continue
                column_name = (
                    output_name if len(components) == 1 else f"{output_name}[{i}]"
                )
                column = {}
                for input_name, value in component.items():
                    values = atleast_1d(value).ravel()
                    if values.size == 1:
                        column[input_name] = float(values[0])
                    else:
                        column.update({
                            f"{input_name}[{j}]": float(v) for j, v in enumerate(values)
                        })
                columns[column_name] = column
    except (TypeError, ValueError, AttributeError):
        return None

    return DataFrame(columns) if columns else None
