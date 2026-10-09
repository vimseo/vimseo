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
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.string_tools import MultiLineString
from pydantic import Field

from vimseo.core.model_metadata import MetaDataNames
from vimseo.tools.base_tool import BaseResult
from vimseo.tools.doe.doe_plots import create_curve_figures
from vimseo.tools.doe.doe_plots import create_scalar_outputs_figure
from vimseo.tools.doe.doe_plots import create_scatter_matrix
from vimseo.tools.doe.doe_plots import get_scalar_names
from vimseo.tools.doe.doe_plots import get_varying_names
from vimseo.tools.post_tools.plot_parameters import Plot
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.tools.result_visualization import Figure


class DOEVisualizationSettings(BaseVisualizationSettings):
    abscissa_name: str = Field(
        default="",
        description="The name of the input used as abscissa of the parametric study. "
        "If empty, use the only input varying from a sample to another, if any.",
    )
    output_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the outputs to visualize. "
        "If empty, use all the outputs.",
    )
    scatter_matrix_variable_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the scalar variables of the scatter matrix. "
        "If empty, use all the scalar inputs and outputs.",
    )


@dataclass
class DOEResult(BaseResult):
    """The result of a DOE."""

    _VISUALIZATION_SETTINGS: ClassVar[type[DOEVisualizationSettings]] = (
        DOEVisualizationSettings
    )

    dataset: Dataset | None = None
    """The dataset resulting from the DOE."""

    plots: list[Plot] = field(default_factory=list)
    """The figures of the model, from its ``PLOTS`` and the ones of its load case.

    They are stored in the result since the description of the model does not hold
    them."""

    def __str__(self):
        msg = MultiLineString()
        msg.add(dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder))
        msg.add("")
        msg.add(
            "============================= DOE Tool Results ========================="
        )
        msg.add(str(self.dataset))
        return str(msg)

    def _get_input_and_output_names(self) -> tuple[list[str], list[str]]:
        """Return the names of the inputs and of the informative outputs.

        The metadata of the model, except the CPU time, are not informative.
        """
        input_names = (
            self.dataset.get_variable_names(IODataset.INPUT_GROUP)
            if IODataset.INPUT_GROUP in self.dataset.group_names
            else []
        )
        output_names = [
            name
            for name in self.dataset.variable_names
            if name not in input_names
            and (name not in set(MetaDataNames) or name == MetaDataNames.cpu_time)
        ]
        return input_names, output_names

    def get_visualization_choices(self) -> dict[str, list[str]]:
        if self.dataset is None or self.dataset.empty:
            return {}
        data = self.dataset.to_dict_of_arrays(by_group=False)
        input_names, output_names = self._get_input_and_output_names()
        return {
            "scatter_matrix_variable_names": get_scalar_names(
                data, dict.fromkeys([*input_names, *output_names])
            ),
            "output_names": output_names,
        }

    def _create_figures(self, settings: DOEVisualizationSettings) -> dict[str, Figure]:
        if self.dataset is None or self.dataset.empty:
            return {}

        from vimseo.tools.post_tools.plot_parameters import create_plot

        data = self.dataset.to_dict_of_arrays(by_group=False)
        input_names, output_names = self._get_input_and_output_names()
        output_names = list(settings.output_names) or output_names

        figures = {}
        scatter_matrix = create_scatter_matrix(
            data,
            get_scalar_names(
                data,
                settings.scatter_matrix_variable_names
                or dict.fromkeys([*input_names, *output_names]),
            ),
        )
        if scatter_matrix is not None:
            figures["scatter_matrix"] = scatter_matrix

        abscissa_name = settings.abscissa_name
        if not abscissa_name:
            varying_names = get_varying_names(data, input_names)
            abscissa_name = varying_names[0] if len(varying_names) == 1 else ""

        model = self.metadata.model
        if abscissa_name:
            scalar_output_names = get_scalar_names(data, output_names)
            if scalar_output_names:
                title = f"{abscissa_name} study"
                if model is not None:
                    title = f"{model.name} / {model.load_case.name} - {title}"
                figures[f"scalar_outputs_vs_{abscissa_name}"] = (
                    create_scalar_outputs_figure(
                        data, abscissa_name, scalar_output_names, title
                    )
                )
            labels = [
                f"{abscissa_name} = {value:g}" for value in data[abscissa_name][:, 0]
            ]
        else:
            labels = [f"sample {i}" for i in range(len(self.dataset))]

        if self.plots:
            figures.update(
                create_curve_figures(
                    {
                        name: values
                        for name, values in data.items()
                        if name in input_names or name in output_names
                    },
                    [create_plot(plot) for plot in self.plots],
                    labels,
                )
            )
        return figures

    def get_key_values(self) -> dict[str, float]:
        if self.dataset is None:
            return {}
        return {"n_samples": float(len(self.dataset))}
