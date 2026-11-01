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

import logging
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Literal

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.string_tools import MultiLineString
from pydantic import Field

from vimseo.analysis_nodes.base_analysis_node import BaseResult
from vimseo.analysis_nodes.doe.doe_plots import create_curve_figures
from vimseo.analysis_nodes.doe.doe_plots import create_sample_curve_sets
from vimseo.analysis_nodes.doe.doe_plots import create_scalar_outputs_figure
from vimseo.analysis_nodes.doe.doe_plots import create_scatter_matrix
from vimseo.analysis_nodes.doe.doe_plots import get_scalar_names
from vimseo.analysis_nodes.doe.doe_plots import get_varying_names
from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import Plot
from vimseo.analysis_nodes.result_visualization import BasePlotSettings
from vimseo.analysis_nodes.result_visualization import plot_family
from vimseo.core.model_metadata import MetaDataNames
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from numpy import ndarray
    from pandas import DataFrame

    from vimseo.analysis_nodes.result_visualization import Figure

LOGGER = logging.getLogger(__name__)


class DOEVisualizationSettings(BasePlotSettings):
    abscissa_name: str = Field(
        default="",
        description="The name of the input used as abscissa of the parametric study. "
        "If empty, use the only input varying from a sample to another, if any. "
        "The study is drawn for the samples differing by this input only, so it is "
        "not drawn for a design varying the inputs jointly, e.g. a LHS.",
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
    family_layout: Literal["one_figure", "one_figure_per_family"] = Field(
        default="one_figure",
        description="When several inputs vary, the parametric study is drawn per "
        "family, i.e. per set of samples differing by the abscissa only: the scalar "
        "outputs of all the families in one figure, a line per family, or in a "
        "figure per family. The curves are always drawn in a figure per family.",
    )


@dataclass
class DOEResult(BaseResult):
    """The result of a DOE."""

    _PLOT_SETTINGS: ClassVar[type[DOEVisualizationSettings]] = DOEVisualizationSettings

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
            "============================= DOE Analysis Node Results ========================="
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

    def get_plot_choices(self) -> dict[str, list[str]]:
        if self.dataset is None or self.dataset.empty:
            return {}
        data = self.dataset.to_dict_of_arrays(by_group=False)
        input_names, output_names = self._get_input_and_output_names()
        choices = {
            "scatter_matrix_variable_names": get_scalar_names(
                data, dict.fromkeys([*input_names, *output_names])
            ),
            "output_names": output_names,
            # A parametric study is drawn along an input forming families.
            "abscissa_name": list(self.get_families()),
        }
        return {name: values for name, values in choices.items() if values}

    def get_families(self) -> dict[str, dict[str, list[int]]]:
        """Return the families of samples differing by a single input.

        Returns:
            The families along each input forming some, as the indices of the samples
            of each family bound to the values of the other varying inputs, e.g.
            ``"width=20.0"``, the key being empty when this input is the only varying
            one. Empty when no family exists, e.g. for a LHS varying the inputs
            jointly.
        """
        if self.dataset is None or self.dataset.empty:
            return {}
        data = self.dataset.to_dict_of_arrays(by_group=False)
        input_names, _ = self._get_input_and_output_names()
        families = {
            name: self._get_families(data, input_names, name)[0]
            for name in get_varying_names(data, input_names)
        }
        return {name: family for name, family in families.items() if family}

    @staticmethod
    def _get_input_table(
        data: Mapping[str, ndarray], input_names: Sequence[str]
    ) -> DataFrame:
        """Return the scalar inputs, a row per sample, named ``inputs.{name}``."""
        from pandas import DataFrame

        from vimseo.results.operations import INPUT_PREFIX

        return DataFrame({
            f"{INPUT_PREFIX}{name}": data[name][:, 0]
            for name in get_scalar_names(data, input_names)
        })

    @classmethod
    def _get_families(
        cls, data: Mapping[str, ndarray], input_names: Sequence[str], along: str
    ) -> tuple[dict[str, list[int]], list[int]]:
        """Return the families of samples differing by a single input.

        Args:
            data: The values of the variables, shaped as ``(n_samples, size)``.
            input_names: The names of the inputs.
            along: The name of the input varying in a family.

        Returns:
            The indices of the samples of each family, sorted by ``along`` and bound
            to the values of the other varying inputs, e.g. ``"width=20.0"``, empty
            when ``along`` is the only varying input, and the indices of the samples
            belonging to no family.
        """
        from vimseo.results.collection import FamilyKey
        from vimseo.results.operations import group_by_variation

        families, ungrouped = group_by_variation(
            cls._get_input_table(data, input_names), along
        )
        return {
            "" if not key else str(FamilyKey(key)): rows
            for key, rows in families.items()
        }, ungrouped

    def _create_figures(self, settings: DOEVisualizationSettings) -> dict[str, Figure]:
        if self.dataset is None or self.dataset.empty:
            return {}

        from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import (
            create_plot,
        )

        data = self.dataset.to_dict_of_arrays(by_group=False)
        input_names, output_names = self._get_input_and_output_names()
        output_names = list(settings.output_names) or output_names

        figures = {}
        # By default, the constant variables are left out: their histograms cannot
        # be drawn.
        scatter_matrix = create_scatter_matrix(
            data,
            get_scalar_names(data, settings.scatter_matrix_variable_names)
            if settings.scatter_matrix_variable_names
            else get_varying_names(data, dict.fromkeys([*input_names, *output_names])),
        )
        if scatter_matrix is not None:
            figures["scatter_matrix"] = scatter_matrix

        abscissa_name = settings.abscissa_name
        if not abscissa_name:
            varying_names = get_varying_names(data, input_names)
            abscissa_name = varying_names[0] if len(varying_names) == 1 else ""

        model = self.metadata.model
        data = {
            name: values
            for name, values in data.items()
            if name in input_names or name in output_names
        }
        plots = [create_plot(plot) for plot in self.plots]
        if abscissa_name:
            title = f"{abscissa_name} study"
            if model is not None:
                title = f"{model.name} / {model.load_case.name} - {title}"
            figures.update(
                self._plot_families(
                    data,
                    input_names,
                    output_names,
                    plots,
                    abscissa_name,
                    title,
                    settings,
                )
            )
        elif plots:
            figures.update(
                create_curve_figures(data, plots, self._get_labels(data, input_names))
            )
        return figures

    def _get_labels(
        self, data: Mapping[str, ndarray], input_names: Sequence[str]
    ) -> list[str]:
        """Return a label per sample, from its varying inputs, else its index."""
        from vimseo.results.operations import get_labels

        table = self._get_input_table(data, input_names)
        table["sample"] = [f"sample {i}" for i in range(len(self.dataset))]
        return get_labels(table, "sample", ())

    def _plot_families(
        self,
        data: Mapping[str, ndarray],
        input_names: Sequence[str],
        output_names: Sequence[str],
        plots: Sequence[Plot],
        abscissa_name: str,
        title: str,
        settings: DOEVisualizationSettings,
    ) -> dict[str, Figure]:
        """Create the figures of the parametric study, per family of samples.

        A figure of a family is suffixed by the values of the other varying inputs,
        e.g. ``curves_dplt_vs_dplt_grid[width=20.0]``, unless a single input varies.

        Args:
            data: The values of the variables, shaped as ``(n_samples, size)``.
            input_names: The names of the inputs.
            output_names: The names of the outputs.
            plots: The figures of the model.
            abscissa_name: The name of the input varying in a family.
            title: The title of the figure of the scalar outputs.
            settings: The settings of the figures.

        Returns:
            The figures.
        """
        families, ungrouped = self._get_families(data, input_names, abscissa_name)
        if ungrouped:
            LOGGER.warning(
                f"{len(ungrouped)} samples belong to no family along {abscissa_name}, "
                "i.e. no other sample differs from them by this input only, so they "
                "are left out of its parametric study; the inputs probably vary "
                "jointly, as in a LHS: see the scatter matrix."
            )

        scalar_output_names = get_scalar_names(data, output_names)
        curve_sets = create_sample_curve_sets(data, plots, len(self.dataset))
        scalars = [
            {name: data[name][i, 0] for name in scalar_output_names}
            for i in range(len(self.dataset))
        ]
        figures = {}
        for key, samples in families.items():
            suffix = f"[{key}]" if key else ""
            family_figures = plot_family(
                [curve_sets[i] for i in samples],
                data[abscissa_name][samples, 0],
                [scalars[i] for i in samples],
                abscissa_name,
                f"{title} - {key}" if key else title,
            )
            for name, figure in family_figures.items():
                if (
                    settings.family_layout == "one_figure_per_family"
                    or name.startswith("curves_")
                    or not key
                ):
                    figures[f"{name}{suffix}"] = figure

        if (
            settings.family_layout == "one_figure"
            and any(families)
            and scalar_output_names
        ):
            figures[f"scalar_outputs_vs_{abscissa_name}"] = (
                create_scalar_outputs_figure(
                    data, abscissa_name, scalar_output_names, title, families
                )
            )
        return figures

    def get_key_values(self) -> dict[str, float]:
        if self.dataset is None:
            return {}
        return {"n_samples": float(len(self.dataset))}
