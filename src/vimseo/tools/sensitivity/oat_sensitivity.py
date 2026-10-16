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
"""A star One-factor-at-a-Time (OAT) sensitivity analysis."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import plotly.graph_objects as go
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import abs as np_abs
from numpy import cumsum
from numpy import errstate
from numpy import nan
from numpy import where
from pydantic import Field
from pydantic import PositiveFloat

from vimseo.algos.doe.star_doe.settings.star_doe_settings import StarDOE_Settings
from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.doe.doe_result import DOEResult
from vimseo.tools.sensitivity.doe_samples import check_no_nan_output
from vimseo.tools.sensitivity.doe_samples import get_algo_settings
from vimseo.tools.sensitivity.doe_samples import get_input_samples
from vimseo.tools.sensitivity.doe_samples import get_output_names
from vimseo.tools.sensitivity.doe_samples import get_variable_names
from vimseo.tools.sensitivity.doe_samples import to_io_dataset
from vimseo.tools.sensitivity.oat_sensitivity_result import OATIndices
from vimseo.tools.sensitivity.oat_sensitivity_result import OATSensitivityResult

if TYPE_CHECKING:
    from collections.abc import Mapping

    from gemseo.typing import RealArray

LOGGER = logging.getLogger(__name__)

_STAR_SETTINGS = StarDOE_Settings.model_fields
"""The settings of the star DOE."""


class OATSensitivitySettings(BaseSettings):
    output_names: list[str] = Field(
        default=[],
        description="The names of the outputs to consider. "
        "If empty, use all the outputs of the model, or of the DOE samples, "
        "except the metadata of the model.",
    )
    center: dict[str, float | list[float]] = Field(
        default={}, description=_STAR_SETTINGS["center"].description
    )
    relative_step: PositiveFloat = Field(
        default=0.05, description=_STAR_SETTINGS["relative_step"].description
    )
    two_sided: bool = Field(
        default=True, description=_STAR_SETTINGS["two_sided"].description
    )
    fallback_step: PositiveFloat = Field(
        default=0.05, description=_STAR_SETTINGS["fallback_step"].description
    )


class OATSensitivityInputs(BaseInputs):
    model: IntegratedModel | None = None
    parameter_space: ParameterSpace = ParameterSpace()
    doe_result: DOEResult | None = Field(
        default=None,
        description="The result of a star DOE prepared in advance, "
        "i.e. of a DOETool executed with the algo 'StarDOE'. "
        "If ``None``, execute the star DOE on the model over the parameter space.",
    )


class OATSensitivityTool(BaseAnalysisTool):
    """Run a star One-factor-at-a-Time sensitivity analysis.

    The outputs of an :class:`~.IntegratedModel` are computed at the center of a star
    and when each input component varies alone, using the DOE algorithm
    ``"StarDOE"``; the result of a star DOE prepared in advance can be used instead.

    See :class:`.OATSensitivityResult` for the definition of the indices.
    """

    result: OATSensitivityResult

    _INPUTS = OATSensitivityInputs

    _SETTINGS = OATSensitivitySettings

    _STAR_SETTING_NAMES = ("center", "relative_step", "two_sided", "fallback_step")
    """The names of the settings of the star DOE."""

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            subtools=[DOETool()],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )
        self.result = OATSensitivityResult()

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: OATSensitivityInputs | None = None,
        settings: OATSensitivitySettings | None = None,
        **options,
    ) -> OATSensitivityResult:
        model = options["model"]
        if model is not None:
            self.result.metadata.model = model.description

        doe_result = options["doe_result"]
        if doe_result is None:
            if model is None:
                msg = "Either a model or the result of a star DOE must be provided."
                raise ValueError(msg)

            doe_result = self._subtools["DOETool"].execute(
                model=model,
                parameter_space=options["parameter_space"],
                output_names=options["output_names"]
                or model.get_output_data_names(remove_metadata=True),
                algo="StarDOE",
                algo_settings={
                    name: options[name] for name in self._STAR_SETTING_NAMES
                },
            )
        else:
            self._subtools["DOETool"].result = doe_result
            ignored_names = [
                name
                for name in self._STAR_SETTING_NAMES
                if options[name] != OATSensitivitySettings.model_fields[name].default
            ]
            if ignored_names:
                LOGGER.warning(
                    "The settings %s are ignored since the result of a star DOE "
                    "is provided.",
                    ignored_names,
                )
            self.result.metadata.report["doe_dataset_name"] = doe_result.dataset.name

        two_sided = StarDOE_Settings(
            **get_algo_settings(doe_result, ("StarDOE",), "OAT")
        ).two_sided
        doe_dataset = doe_result.dataset
        output_names = get_output_names(doe_dataset, options["output_names"])
        self.result.metadata.report["output_names"] = output_names
        dataset = to_io_dataset(doe_dataset, output_names)
        dimension = dataset.group_names_to_n_components[IODataset.INPUT_GROUP]
        n_samples = (2 if two_sided else 1) * dimension + 1
        if len(dataset) != n_samples:
            msg = (
                f"The star DOE has {len(dataset)} samples, whereas a "
                f"{'two' if two_sided else 'one'}-sided star with {dimension} input "
                f"components has {n_samples}; an evaluation of the model may have "
                "failed."
            )
            raise ValueError(msg)

        check_no_nan_output(dataset, "OAT")
        self.result.two_sided = two_sided
        self.result.dataset = dataset
        self.__compute_indices(dataset, output_names)
        return self.result

    def __compute_indices(self, dataset: IODataset, output_names: list[str]) -> None:
        """Compute the OAT indices.

        Args:
            dataset: The samples of the star DOE.
            output_names: The names of the outputs.
        """
        samples = get_input_samples(dataset)
        dimension = samples.shape[1]
        components = range(dimension)
        center = samples[0]
        steps_plus = samples[1 : dimension + 1][components, components] - center
        two_sided = self.result.two_sided
        if two_sided:
            steps_minus = samples[dimension + 1 :][components, components] - center

        input_names = get_variable_names(dataset, IODataset.INPUT_GROUP)
        input_sizes = [
            dataset.variable_names_to_n_components[name] for name in input_names
        ]
        self.result.center = _split(center, input_names, input_sizes)
        self.result.input_steps = _split(steps_plus, input_names, input_sizes)
        zero_center_names = self.result.get_zero_center_names()
        if zero_center_names:
            LOGGER.warning(
                "The center of %s is zero: its step is not relative to its center "
                "but derived from its standard deviation, its bounds or the absolute "
                "fallback_step, so its OAT indices are not comparable with those of "
                "the other inputs and may mislead the ranking.",
                zero_center_names,
            )
            self.result.metadata.report["inputs_with_non_relative_step"] = (
                zero_center_names
            )

        indices: OATIndices = {}
        for output_name in output_names:
            outputs = (
                dataset
                .get_view(
                    group_names=IODataset.OUTPUT_GROUP, variable_names=output_name
                )
                .to_numpy()
                .astype(float)
            )
            f_0 = outputs[0]
            f_plus = outputs[1 : dimension + 1]
            output_indices = {"delta_f_plus": f_plus - f_0}
            if two_sided:
                f_minus = outputs[dimension + 1 :]
                output_indices["delta_f_minus"] = f_minus - f_0
                output_indices["delta_f"] = (f_plus - f_minus) / 2
                output_indices["gradient"] = (f_plus - f_minus) / (
                    steps_plus - steps_minus
                )[:, None]
            else:
                output_indices["delta_f"] = f_plus - f_0
                output_indices["gradient"] = (f_plus - f_0) / steps_plus[:, None]

            if (f_0 == 0).any():
                LOGGER.warning(
                    "The output %s is zero at the center of the star "
                    "for some components; their relative indices are NaN.",
                    output_name,
                )
            with errstate(divide="ignore", invalid="ignore"):
                output_indices["relative_delta_f"] = where(
                    f_0 == 0, nan, output_indices["delta_f"] / np_abs(f_0)
                )

            for index_name, values in output_indices.items():
                indices.setdefault(index_name, {})[output_name] = [
                    _split(values[:, j], input_names, input_sizes)
                    for j in range(values.shape[1])
                ]

        self.result.indices = indices

    def plot_results(
        self,
        result: OATSensitivityResult,
        output_names=(),
        directory_path: str | Path = "",
        save=False,
        show=True,
    ) -> Mapping[str, go.Figure]:
        """Plot a tornado diagram for each component of the outputs.

        The bars show the variations of the output from the center of the star
        when each input component varies alone,
        sorted by decreasing absolute centered variation ``delta_f``.

        Args:
            output_names: The names of the outputs.
                If empty, use all the outputs of the analysis.

        Returns:
            The tornado diagrams.
        """
        directory_path = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )
        output_names = output_names or list(result.indices["delta_f"])
        figures = {}
        for output_name in output_names:
            n_components = len(result.indices["delta_f"][output_name])
            for j in range(n_components):
                label = output_name if n_components == 1 else f"{output_name}[{j}]"
                figure = _create_tornado(result, output_name, j, label)
                figures[f"tornado_{label}"] = figure
                if save:
                    figure.write_html(directory_path / f"tornado_{label}.html")
                if show:
                    figure.show()

        return figures


def _split(
    values: RealArray, names: list[str], sizes: list[int]
) -> dict[str, RealArray]:
    """Split the values of input components by input variable.

    Args:
        values: The values of the input components.
        names: The names of the input variables.
        sizes: The sizes of the input variables.

    Returns:
        The values of the input variables.
    """
    ends = cumsum(sizes)
    return {
        name: values[end - size : end]
        for name, size, end in zip(names, sizes, ends, strict=True)
    }


def _create_tornado(
    result: OATSensitivityResult, output_name: str, component: int, label: str
) -> go.Figure:
    """Create a tornado diagram for an output component.

    Args:
        result: The result of the OAT sensitivity analysis.
        output_name: The name of the output.
        component: The component of the output.
        label: The label of the output component.

    Returns:
        The tornado diagram.
    """
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
