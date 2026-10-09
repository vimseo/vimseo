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

from collections import defaultdict
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import ClassVar

from gemseo.algos.design_space import DesignSpace
from numpy import array
from numpy import ndarray
from pandas import DataFrame
from plotly.graph_objs import Figure
from pydantic import Field
from pydantic import PositiveInt

from vimseo.tools.base_result import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import create_figure
from vimseo.tools.result_visualization import flatten_numbers
from vimseo.tools.result_visualization import to_cell
from vimseo.utilities.model_data import MetricVariableType

CurveDataType = Mapping[str, list[Mapping[str, DataFrame]]]


def get_name(namespaced_name: str) -> str:
    """Return the name from a namespaced name."""
    return namespaced_name.split(":")[1]


def get_namespace(namespaced_name: str) -> str:
    """Return the namespace from a namespaced name."""
    return namespaced_name.split(":")[0]


def get_metric_curve_names(metric_variables: Iterable) -> list[tuple[str, str]]:
    """Return the names of ``x`` and ``y`` for each curve of the metric variables.

    Args:
        metric_variables: The metric variables.
    """
    return [
        (metric_variable.mesh, metric_variable.name)
        for metric_variable in metric_variables
        if metric_variable.type == MetricVariableType.CURVE
    ]


def get_metric_scalar_names(metric_variables: Iterable) -> list[str]:
    """Return the names of the scalars of the metric variables.

    Args:
        metric_variables: The metric variables.
    """
    return [
        metric_variable.name
        for metric_variable in metric_variables
        if metric_variable.type == MetricVariableType.SCALAR
    ]


class CalibrationStepVisualizationSettings(BaseVisualizationSettings):
    load_cases: tuple[str, ...] = Field(
        default=(),
        description="The load cases whose simulated versus reference plots are shown. "
        "If empty, use all the load cases of the calibration step.",
    )
    font_size: PositiveInt = Field(default=12, description="The font size.")


@dataclass
class CurveData:
    posterior_dataframes: CurveDataType | None = None

    prior_dataframes: CurveDataType | None = None

    reference_dataframes: CurveDataType | None = None


@dataclass
class CalibrationStepResult(BaseResult):
    """The result of a calibration step."""

    _VISUALIZATION_SETTINGS: ClassVar[type[CalibrationStepVisualizationSettings]] = (
        CalibrationStepVisualizationSettings
    )

    posterior_parameters: Mapping[str, ndarray] | None = field(
        default=None, metadata="The calibrated parameters."
    )

    prior_parameters: Mapping[str, ndarray] | None = None

    reference_data: Mapping[str, ndarray] | None = None

    design_space: DesignSpace | None = None

    prior_model_data: Mapping[str, ndarray] | None = None

    posterior_model_data: Mapping[str, ndarray] | None = None

    metric_variables: Mapping[str, tuple[str]] | None = None

    post_processing_figures: Mapping[str, Figure] | None = field(
        default=None,
        metadata="The figures showing the optimization convergence history.",
    )

    curve_data: Iterable[CurveDataType | None] = field(default_factory=CurveData)

    objective: str = ""

    def _create_figures(
        self, settings: CalibrationStepVisualizationSettings
    ) -> dict[str, Figure | dict[str, Figure]]:
        from gemseo.datasets.dataset import Dataset
        from gemseo.post.dataset.bars import BarPlot

        from vimseo.tools.post_tools.calibration_plots import CalibrationCurves

        figures = defaultdict(dict)
        load_cases = settings.load_cases
        metric_variables = self.metric_variables or ()

        for namespaced_name in get_metric_scalar_names(metric_variables):
            load_case = get_namespace(namespaced_name)
            if load_cases and load_case not in load_cases:
                continue
            name = get_name(namespaced_name)
            categories = ["prior", "posterior", "reference"]
            df = DataFrame.from_dict({
                category: array(data_source[namespaced_name]).flatten()
                for category, data_source in zip(
                    categories,
                    [
                        self.prior_model_data,
                        self.posterior_model_data,
                        self.reference_data,
                    ],
                    strict=False,
                )
            }).T
            df.columns = [str(c) for c in df.columns]
            plot = BarPlot(Dataset.from_dataframe(df))
            plot.title = (
                f"Simulated versus reference for output {name} "
                f"and load case {load_case}"
            )
            plot.font_size = settings.font_size
            plot.labels = categories
            figures[load_case][f"simulated_versus_reference_{name}_bars"] = (
                plot.execute(save=False, show=False, file_format="html")[0]
            )

        for abscissa_name, namespaced_name in get_metric_curve_names(metric_variables):
            load_case = get_namespace(namespaced_name)
            if load_cases and load_case not in load_cases:
                continue
            name = get_name(namespaced_name)
            key = (
                f"simulated_versus_reference_curve_{name}_versus_"
                f"{get_name(abscissa_name)}"
            )
            figures[load_case][key] = create_figure(
                CalibrationCurves,
                self.curve_data.posterior_dataframes[load_case],
                self.curve_data.prior_dataframes[load_case],
                self.curve_data.reference_dataframes[load_case],
                get_name(abscissa_name),
                name,
                load_case=load_case,
                font_size=settings.font_size,
            )

        # The figures of the calibration scenario, created by the tool.
        for key, value in (self.post_processing_figures or {}).items():
            if isinstance(value, Mapping):
                if not load_cases or key in load_cases:
                    figures[key].update(value)
            else:
                figures[key] = value

        if self.prior_parameters and self.posterior_parameters:
            figures["prior_versus_posterior_parameters"] = (
                self._plot_prior_versus_posterior_parameters(settings.font_size)
            )

        return figures

    def _plot_prior_versus_posterior_parameters(self, font_size: int) -> Figure:
        """Plot the prior and posterior values of the parameters as bars.

        Args:
            font_size: The font size.
        """
        from gemseo.datasets.dataset import Dataset
        from gemseo.post.dataset.bars import BarPlot

        df = DataFrame.from_dict({
            name: array(values).flatten()
            for name, values in self._get_parameters().items()
        })
        plot = BarPlot(Dataset.from_dataframe(df))
        plot.title = "Comparison of prior and posterior parameters"
        plot.font_size = font_size
        plot.labels = ["prior", "posterior"]
        return plot.execute(save=False, show=False, file_format="html")[0]

    def _get_parameters(self) -> dict[str, list]:
        """Return the prior and posterior values of each parameter."""
        parameters = defaultdict(list)
        for values in [self.prior_parameters, self.posterior_parameters]:
            for name, value in values.items():
                parameters[name].append(value)
        return parameters

    def _create_tables(self) -> dict[str, DataFrame]:
        tables = super()._create_tables()
        tables.pop("prior_parameters", None)
        tables.pop("posterior_parameters", None)
        if self.prior_parameters and self.posterior_parameters:
            tables["parameters"] = DataFrame.from_dict(
                {
                    name: [to_cell(value) for value in values]
                    for name, values in self._get_parameters().items()
                },
                orient="index",
                columns=["prior", "posterior"],
            )
        return tables

    def get_key_values(self) -> dict[str, float]:
        return flatten_numbers({"posterior": self.posterior_parameters or {}})
