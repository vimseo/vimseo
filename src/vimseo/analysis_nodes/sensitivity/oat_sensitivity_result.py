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
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.datasets.dataset import Dataset
from gemseo.typing import RealArray
from gemseo.utils.string_tools import MultiLineString
from pydantic import Field

from vimseo.analysis_nodes.base_analysis_node import BaseResult
from vimseo.analysis_nodes.result_visualization import BasePlotSettings
from vimseo.analysis_nodes.result_visualization import flatten_numbers
from vimseo.analysis_nodes.sensitivity.indices import flatten_components
from vimseo.analysis_nodes.sensitivity.indices import indices_to_dataframe
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from pandas import DataFrame

    from vimseo.analysis_nodes.result_visualization import Figure

OATIndices = dict[str, dict[str, list[dict[str, "RealArray"]]]]
"""The OAT indices, as ``{index_name: {output_name: [{input_name: values}]}}``.

The list has an item per output component and ``values`` has an item per input
component."""


class OATSensitivityPlotSettings(BasePlotSettings):
    output_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the outputs whose tornado diagrams are shown. "
        "If empty, use all the outputs of the analysis.",
    )


@dataclass
class OATSensitivityResult(BaseResult):
    r"""The result of a star One-factor-at-a-Time (OAT) sensitivity analysis.

    The indices are computed from the outputs :math:`f_0` at the center :math:`x_0`
    of the star, :math:`f^+_i` at :math:`x_0+h^+_ie_i`
    and, for a two-sided star, :math:`f^-_i` at :math:`x_0+h^-_ie_i`
    with :math:`h^-_i<0`:

    - ``delta_f_plus``: :math:`f^+_i-f_0`,
    - ``delta_f_minus``: :math:`f^-_i-f_0` (two-sided star only),
    - ``delta_f``: :math:`(f^+_i-f^-_i)/2` for a two-sided star,
      :math:`f^+_i-f_0` otherwise,
    - ``relative_delta_f``: ``delta_f`` divided by :math:`|f_0|`
      (NaN when :math:`f_0=0`),
    - ``gradient``: :math:`(f^+_i-f^-_i)/(h^+_i-h^-_i)` for a two-sided star
      (centered finite difference),
      :math:`(f^+_i-f_0)/h^+_i` otherwise.
    """

    _PLOT_SETTINGS: ClassVar[type[OATSensitivityPlotSettings]] = (
        OATSensitivityPlotSettings
    )

    dataset: Dataset | None = None
    """The samples of the star DOE, restricted to the inputs and the analyzed
    outputs."""

    indices: OATIndices = field(default_factory=dict)
    """The OAT indices."""

    center: dict[str, RealArray] = field(default_factory=dict)
    """The center of the star."""

    input_steps: dict[str, RealArray] = field(default_factory=dict)
    r"""The physical steps :math:`h^+_i` of the inputs."""

    two_sided: bool = True
    """Whether the star is two-sided."""

    def get_indices_dataframe(self, index_name: str = "delta_f") -> DataFrame:
        """Return OAT indices as a table.

        Args:
            index_name: The name of the indices.

        Returns:
            The indices, with a row per input component
            and a column per output component.
        """
        return indices_to_dataframe(self.indices[index_name])

    def sort_input_variables(
        self, output_name: str, output_component: int = 0
    ) -> list[str]:
        r"""Sort the input components by decreasing absolute ``delta_f``.

        ``delta_f`` is the centered variation :math:`(f^+_i-f^-_i)/2`
        for a two-sided star, :math:`f^+_i-f_0` otherwise.

        Args:
            output_name: The name of the output.
            output_component: The component of the output.

        Returns:
            The names of the input components,
            from the most influential one to the least influential one.
        """
        values = flatten_components(
            self.indices["delta_f"][output_name][output_component]
        )
        return sorted(values, key=lambda name: abs(values[name]), reverse=True)

    def get_zero_center_names(self) -> list[str]:
        """Return the input components whose center is zero.

        Their step is not relative to their center,
        so their indices are not comparable with those of the other components.

        Returns:
            The names of the input components whose center is zero.
        """
        return [
            name
            for name, value in flatten_components(self.center).items()
            if value == 0
        ]

    def get_plot_choices(self) -> dict[str, list[str]]:
        output_names = list(self.indices.get("delta_f", {}))
        return {"output_names": output_names} if output_names else {}

    def _create_figures(
        self, settings: OATSensitivityPlotSettings
    ) -> dict[str, Figure]:
        """Create a tornado diagram for each component of the outputs.

        The bars show the variations of the output from the center of the star
        when each input component varies alone,
        sorted by decreasing absolute centered variation ``delta_f``.
        """
        delta_f = self.indices.get("delta_f", {})
        figures = {}
        for output_name in settings.output_names or list(delta_f):
            n_components = len(delta_f[output_name])
            for j in range(n_components):
                label = output_name if n_components == 1 else f"{output_name}[{j}]"
                figures[f"tornado_{label}"] = _create_tornado(
                    self, output_name, j, label
                )
        return figures

    def _create_tables(self) -> dict[str, DataFrame]:
        tables = super()._create_tables()
        tables.pop("indices", None)
        for index_name in self.indices:
            tables[f"indices_{index_name}"] = self.get_indices_dataframe(index_name)
        return tables

    def get_key_values(self) -> dict[str, float]:
        # The indices by kind, output and input, e.g. "delta_f.y.x1".
        return flatten_numbers({
            index_name: self.get_indices_dataframe(index_name).to_dict()
            for index_name in self.indices
        })

    def __str__(self) -> str:
        text = MultiLineString()
        text.add("Results of a star One-factor-at-a-Time sensitivity analysis.")
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        text.add("")
        text.add("Input variables by decreasing absolute centered variation delta_f:")
        text.indent()
        for output_name, components in self.indices.get("delta_f", {}).items():
            for i, component in enumerate(components):
                values = flatten_components(component)
                ranking = ", ".join(
                    f"{name} ({values[name]:.4g})"
                    for name in self.sort_input_variables(output_name, i)
                )
                text.add(f"For output {output_name}[{i}]: {ranking}.")
        zero_center_names = self.get_zero_center_names()
        if zero_center_names:
            text.add(
                f"Warning: the steps of {zero_center_names} are not relative to "
                "their zero center; their ranking is not comparable."
            )
        text.dedent()
        for index_name in self.indices:
            text.add("")
            text.add(f"Index {index_name}:")
            text.indent()
            for line in str(self.get_indices_dataframe(index_name)).splitlines():
                text.add(line)
            text.dedent()
        return str(text)


def _create_tornado(
    result: OATSensitivityResult, output_name: str, component: int, label: str
) -> Figure:
    """Create a tornado diagram for an output component.

    Args:
        result: The result of the OAT sensitivity analysis.
        output_name: The name of the output.
        component: The component of the output.
        label: The label of the output component.

    Returns:
        The tornado diagram.
    """
    import plotly.graph_objects as go

    # The most influential input is at the top.
    input_names = result.sort_input_variables(output_name, component)[::-1]
    figure = go.Figure()
    # Explicit colors: a "+ step" bar can lie on the negative side.
    sides = [("delta_f_plus", "+ step", "#1f77b4")]
    if result.two_sided:
        sides.append(("delta_f_minus", "- step", "#d62728"))
    for index_name, name, color in sides:
        values = result.get_indices_dataframe(index_name)[label]
        figure.add_trace(
            go.Bar(
                x=[values[input_name] for input_name in input_names],
                y=input_names,
                orientation="h",
                name=name,
                marker_color=color,
            )
        )

    figure.update_layout(
        barmode="overlay",
        title=f"OAT sensitivity of {label}",
        xaxis_title=f"Variation of {label} from the center of the star",
        yaxis_title="Input",
    )
    return figure
