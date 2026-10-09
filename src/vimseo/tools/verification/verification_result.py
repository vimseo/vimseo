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

"""A verification result and verification case description.."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import atleast_1d
from pandas import DataFrame
from pydantic import Field

from vimseo.tools.base_tool import BaseResult
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import create_figure
from vimseo.tools.result_visualization import flatten_numbers
from vimseo.tools.result_visualization import to_cell
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from vimseo.core.model_description import ModelDescription
    from vimseo.tools.result_visualization import Figure

CASE_DESCRIPTION_TYPE = Mapping[str, str | list[str]]


class VerificationVisualizationSettings(BaseVisualizationSettings):
    metric_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the error metrics to visualize. "
        "If empty, use all the metrics of the verification.",
    )
    output_names: tuple[str, ...] = Field(
        default=(),
        description="The names of the outputs whose error histograms are plotted. "
        "If empty, use all the outputs of the verification.",
    )


class SolutionVerificationCaseVisualizationSettings(BaseVisualizationSettings):
    output_name: str = Field(
        default="",
        description="The name of the output on which convergence is studied. "
        "If empty, use the output of the solution verifications.",
    )
    normalize_index_output: int | None = Field(
        default=None,
        description="The index of the CPU time used to normalize the output, "
        "so that the output of each convergence trajectory is equal to one at this "
        "location. If ``None``, the output is not normalized.",
    )
    dark_mode: bool = Field(default=False, description="Whether to use dark mode.")


@dataclass
class VerificationResult(BaseResult):
    """The result of a verification of a model."""

    _PREFIX_KEY: ClassVar[str] = "reference_name"

    _VISUALIZATION_SETTINGS: ClassVar[type[BaseVisualizationSettings]] = (
        VerificationVisualizationSettings
    )

    simulation_and_reference: Dataset | None = None
    """A Dataset containing the input variables (where the model is executed), the model
    output variables and the reference output variables."""

    element_wise_metrics: Dataset | None = None
    """A Dataset containing the input variables and the metrics comparing the reference
    outputs with the model outputs."""

    integrated_metrics: Mapping[str, Mapping[str, float]] | None = None
    """A dictionary mapping variable names and metric names to integrated metric
    values."""

    description: CASE_DESCRIPTION_TYPE = field(default_factory=dict)
    """A description of the verification case."""

    def _fill_metadata(
        self,
        case_description: CASE_DESCRIPTION_TYPE | None,
        model_description: ModelDescription,
    ):
        """Fill the metadata related to Verification."""
        if case_description:
            self.description = case_description
        self.metadata.model = model_description

    def __str__(self):
        from gemseo.utils.string_tools import MultiLineString

        text = MultiLineString()
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        text.add("Integrated metrics:")
        text.indent()
        for k, v in self.integrated_metrics.items():
            text.add(f"{k}: {v}")
        text.dedent()
        text.add("Element-wise metrics:")
        text.add(repr(self.element_wise_metrics))
        text.add("")
        text.add("Simulation and references:")
        text.add(repr(self.simulation_and_reference))
        text.add("")
        return str(text)

    def _create_figures(
        self, settings: VerificationVisualizationSettings
    ) -> dict[str, Figure]:
        if self.element_wise_metrics is None or not self.integrated_metrics:
            return {}

        from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix

        from vimseo.tools.post_tools.verification_plots import (
            ErrorMetricHistogramPlotter,
        )
        from vimseo.tools.verification.base_verification import comparison_renaming
        from vimseo.tools.verification.base_verification import prepare_overall_dataset
        from vimseo.utilities.datasets import get_nb_input_variables

        figures = {}
        has_several_inputs = get_nb_input_variables(self.element_wise_metrics) > 1
        input_names = self.element_wise_metrics.get_variable_names(
            group_name=IODataset.INPUT_GROUP
        )
        for metric_name in settings.metric_names or tuple(self.integrated_metrics):
            if has_several_inputs:
                dataset = prepare_overall_dataset(
                    self,
                    [metric_name],
                    self.simulation_and_reference.get_variable_names(
                        IODataset.OUTPUT_GROUP
                    ),
                    renamer=comparison_renaming,
                    add_output_data=True,
                )
                figures[f"input_scatter_matrix_{metric_name}"] = ScatterMatrix(
                    dataset, variable_names=input_names, kde=False
                ).execute(save=False, show=False)[0]

            for output_name in settings.output_names or tuple(
                self.integrated_metrics[metric_name]
            ):
                figures[f"error_metric_histogram_{metric_name}_{output_name}"] = (
                    create_figure(
                        ErrorMetricHistogramPlotter,
                        self.element_wise_metrics,
                        metric_name,
                        output_name,
                    )
                )
        return figures

    def get_key_values(self) -> dict[str, float]:
        return flatten_numbers(self.integrated_metrics or {})


@dataclass
class SolutionVerificationResult(VerificationResult):
    """The result of a convergence verification of a model."""

    _VISUALIZATION_SETTINGS: ClassVar[type[BaseVisualizationSettings]] = (
        BaseVisualizationSettings
    )

    cross_validation: dict = field(default_factory=dict)
    """The cross validation on the extrapolated quantities."""

    extrapolation: dict = field(default_factory=dict)
    r"""The extrapolated quantities and associated uncertainty.

    Uncertainty is expressed as the median absolute deviation (MAD). A 95% confidence
    interval, assuming a normal distribution for q and beta, is obtained with $median \pm
    2 MAD$. The Relative Discretization Error (RDE) is given from the finest to the
    coarsest mesh.
    """

    # TODO implement value in execute()
    error_default_element_size: Mapping[str, float] = field(default_factory=dict)
    """The error metrics for the default element size."""

    def __str__(self):
        from gemseo.utils.string_tools import MultiLineString

        text = MultiLineString()
        text.add(super().__str__())
        method = self.extrapolation.get("q_converged_method")
        if method is not None:
            text.add(
                f"Converged value: {self.extrapolation.get('q_converged')} "
                f"(method: {method})"
            )
            if method != "richardson":
                text.add(
                    "  WARNING: Richardson extrapolation failed (nan); a palliative "
                    "was used instead of the reference method."
                )
            text.add("")
        text.add("Richardson extrapolation:")
        text.add(repr(self.extrapolation))
        text.add("")
        text.add("Cross validation on Richardson extrapolation:")
        text.add(repr(self.cross_validation))
        return str(text)

    def _create_figures(self, settings: BaseVisualizationSettings) -> dict[str, Figure]:
        if self.simulation_and_reference is None:
            return {}

        from vimseo.core.model_metadata import MetaDataNames
        from vimseo.tools.post_tools.verification_plots import (
            ConvergenceCrossValidationPlotter,
        )
        from vimseo.tools.post_tools.verification_plots import ConvergenceFitPlotter
        from vimseo.tools.post_tools.verification_plots import (
            ErrorVersusElementSizePlotter,
        )
        from vimseo.tools.post_tools.verification_plots import (
            RelativeErrorVersusCpuTimePlotter,
        )
        from vimseo.tools.post_tools.verification_plots import (
            RelativeErrorVersusElementSizePlotter,
        )
        from vimseo.utilities.file_utils import camel_case_to_snake_case

        plotter_classes = [
            ConvergenceCrossValidationPlotter,
            ConvergenceFitPlotter,
            ErrorVersusElementSizePlotter,
            RelativeErrorVersusElementSizePlotter,
        ]
        if MetaDataNames.cpu_time in self.simulation_and_reference.get_variable_names(
            group_name=IODataset.OUTPUT_GROUP
        ):
            plotter_classes.append(RelativeErrorVersusCpuTimePlotter)

        return {
            # The key does not depend on the suffix of the name of the plotter class.
            camel_case_to_snake_case(
                plotter_class.__name__.removesuffix("Plotter")
            ): create_figure(plotter_class, self)
            for plotter_class in plotter_classes
        }

    def _create_tables(self) -> dict[str, DataFrame]:
        tables = super()._create_tables()
        tables.pop("extrapolation", None)
        tables.pop("cross_validation", None)
        extrapolation = self._get_extrapolation_table()
        if extrapolation is not None:
            tables["extrapolation"] = extrapolation
        if self.cross_validation:
            # A row per fold of the cross validation.
            tables["cross_validation"] = DataFrame.from_dict(
                {
                    fold: {
                        "element_sizes": to_cell(values.get("h")),
                        "extrapolated_value": to_cell(values.get("q_extrap")),
                        "convergence_order": to_cell(values.get("beta")),
                    }
                    for fold, values in self.cross_validation.items()
                },
                orient="index",
            )
        return tables

    def _get_extrapolation_table(self) -> DataFrame | None:
        """Return the extrapolated quantities with their 95% error bands.

        The error band of the extrapolated value and of the convergence order is
        the median plus or minus twice the median absolute deviation.
        """
        extrapolation = self.extrapolation
        if not extrapolation:
            return None

        rows = {}
        for name, key in (
            ("extrapolated_value", "q_extrap"),
            ("convergence_order", "beta"),
        ):
            if key not in extrapolation:
                continue
            value = to_cell(extrapolation[key])
            mad = to_cell(extrapolation.get(f"{key}_mad"))
            has_band = isinstance(value, float) and isinstance(mad, float)
            rows[name] = {
                "value": value,
                "lower_bound": value - 2 * mad if has_band else None,
                "upper_bound": value + 2 * mad if has_band else None,
            }

        for key in ("gci", "gci_1", "gci_2"):
            values = extrapolation.get(key)
            if values is None:
                continue
            bands = extrapolation.get(f"{key}_error_band", [None, None])
            for index, mesh in enumerate(("coarsest", "finest")):
                band = (
                    atleast_1d(bands[index]).ravel() if bands[index] is not None else []
                )
                rows[f"{key}_{mesh}"] = {
                    "value": to_cell(atleast_1d(values).ravel()[index]),
                    "lower_bound": to_cell(band[0]) if len(band) == 2 else None,
                    "upper_bound": to_cell(band[1]) if len(band) == 2 else None,
                }

        if "rde" in extrapolation:
            band = atleast_1d(extrapolation.get("rde_error_band", [])).ravel()
            rows["rde"] = {
                "value": to_cell(extrapolation["rde"]),
                "lower_bound": to_cell(band[0]) if band.size == 2 else None,
                "upper_bound": to_cell(band[1]) if band.size == 2 else None,
            }

        if "q_converged" in extrapolation:
            rows["converged_value"] = {
                "value": to_cell(extrapolation["q_converged"]),
                "lower_bound": None,
                "upper_bound": None,
            }

        return DataFrame.from_dict(rows, orient="index") if rows else None

    def get_key_values(self) -> dict[str, float]:
        key_values = super().get_key_values()
        extrapolation = self._get_extrapolation_table()
        if extrapolation is not None:
            key_values.update(flatten_numbers(extrapolation["value"].to_dict()))
        return key_values


@dataclass
class SolutionVerificationCaseResult(BaseResult):
    """A result from a solution verification case."""

    _VISUALIZATION_SETTINGS: ClassVar[
        type[SolutionVerificationCaseVisualizationSettings]
    ] = SolutionVerificationCaseVisualizationSettings

    convergence_data: DataFrame | None = None
    """A DataFrame containing the convergence data used for the verification."""

    def _create_figures(
        self, settings: SolutionVerificationCaseVisualizationSettings
    ) -> dict[str, Figure]:
        if self.convergence_data is None:
            return {}

        from vimseo.tools.post_tools.verification_case_plots import ConvergenceCase
        from vimseo.tools.post_tools.verification_case_plots import (
            CpuTimeCompromiseCase,
        )

        misc = self.metadata.misc
        return {
            name: create_figure(
                plotter_class,
                self.convergence_data,
                misc["nb_meshes"],
                misc["element_size_variable_name"],
                settings.output_name or misc["output_name"],
                normalize_index_output=settings.normalize_index_output,
                hovering_variables=misc["variable_names"],
                dark_mode=settings.dark_mode,
            )
            for name, plotter_class in (
                ("convergence", ConvergenceCase),
                ("cpu_time_compromise", CpuTimeCompromiseCase),
            )
        }
