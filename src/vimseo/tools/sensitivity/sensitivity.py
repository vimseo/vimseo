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
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.uncertainty import create_sensitivity_analysis
from gemseo.uncertainty import get_available_sensitivity_analyses
from gemseo.utils.directory_creator import DirectoryNamingMethod
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.sensitivity_plot_factory import SensitivityPlotFactory
from vimseo.tools.sensitivity.sensitivity_result import SensitivityResult

if TYPE_CHECKING:
    from collections.abc import Mapping

    from plotly.graph_objs import Figure


LOGGER = logging.getLogger(__name__)


class SensitivityToolSettings_(BaseSettings):
    sensitivity_algo: str = Field(
        default="MorrisAnalysis",
        description="The algorithm used to perform the sensitivity analysis.",
    )
    output_names: list[str] = Field(
        default=[],
        description="The names of the output variables to consider. "
        "If left to default value, all output variables of the model are "
        "considered.",
    )
    n_replicates: int = 5
    n_samples: int = 0


class SensitivityToolSettings(SensitivityToolSettings_):
    """The sensitivity settings."""


class StreamlitSensitivityToolSettings(SensitivityToolSettings_):
    """The sensitivity settings for the workflow dashboard."""


class SensitivityToolInputs(BaseInputs):
    parameter_space: ParameterSpace = ParameterSpace()
    model: IntegratedModel | None = None


class SensitivityTool(BaseAnalysisTool):
    """Run a sensitivity analysis on the outputs of an :class:`~.IntegratedModel` over a
    :class:`~.gemseo.algos.parameter_space.ParameterSpace`."""

    results: SensitivityResult

    _INPUTS = SensitivityToolInputs

    _SETTINGS = SensitivityToolSettings

    _STREAMLIT_SETTINGS = StreamlitSensitivityToolSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )
        self.result = SensitivityResult()
        self.sensitivity_plot_factory = SensitivityPlotFactory()

    @BaseTool.validate
    def execute(
        self,
        inputs: SensitivityToolInputs = None,
        settings: SensitivityToolSettings = None,
        **options,
    ) -> SensitivityResult:
        model = options["model"]
        parameter_space = options["parameter_space"]

        self.result.metadata.model = model.description

        # TODO allow to pass pre-computed samples as an IODataset
        self.result.analysis = create_sensitivity_analysis(
            analysis=options["sensitivity_algo"],
        )

        # algo_settings_dict = {}
        # if (
        #     options["sensitivity_algo"] == "Morris"
        #     or options["sensitivity_algo"] == "MorrisAnalysis"
        # ):
        #     algo_settings = MorrisDOE_Settings
        #     algo_settings_dict["n_samples"] = options["n_replicates"]
        # elif (
        #     options["sensitivity_algo"] == "HSIC"
        #     or options["sensitivity_algo"] == "HSICAnalysis"
        # ):
        #     algo_settings = None
        # else:
        #     raise ValueError(f"{options['sensitivity_algo']} is not handled.")

        output_names = (
            model.get_output_data_names(remove_metadata=True)
            if len(options["output_names"]) == 0
            else options["output_names"]
        )
        self.result.metadata.report["output_names"] = output_names

        if (
            options["sensitivity_algo"] == "MorrisAnalysis"
            or options["sensitivity_algo"] == "Morris"
        ):
            self.result.analysis.compute_samples(
                disciplines=[model],
                parameter_space=parameter_space,
                n_samples=options["n_samples"],
                output_names=output_names,
                n_replicates=options["n_replicates"],
            )
        elif (
            options["sensitivity_algo"] == "HSIC"
            or options["sensitivity_algo"] == "HSICAnalysis"
        ):
            self.result.analysis.compute_samples(
                disciplines=[model],
                parameter_space=parameter_space,
                n_samples=options["n_samples"],
                output_names=(
                    model.get_output_data_names(remove_metadata=True)
                    if len(options["output_names"]) == 0
                    else options["output_names"]
                ),
            )
        else:
            msg = f"{options['sensitivity_algo']} is not handled."
            raise ValueError(msg)

        self.result.indices = self.result.analysis.compute_indices()
        self.result.variable_dimensions = {
            name: parameter_space.distributions[name].dimension
            for name in self.result.analysis.input_names
        }
        self.result.variable_dimensions.update({
            name: len(model.get_output_data()[name]) for name in output_names
        })
        return self.result

    @staticmethod
    def get_available_sensitivity_analyses():
        """Get the available sensitivity analysis."""
        return get_available_sensitivity_analyses()

    def plot_results(
        self,
        result: SensitivityResult,
        output_names=(),
        standardize=False,
        directory_path: str | Path = "",
        save=False,
        show=True,
    ) -> Mapping[str, Figure]:
        """

        Args:
            output_names: The names of the output variable whose sensitivity parameters are
             shown.

        Returns:
            The sensitivity plot.

        """
        output_names = (
            result.metadata.settings["output_names"]
            if len(output_names) == 0
            else output_names
        )
        directory_path = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )

        figures = {}

        if (
            result.metadata.settings["sensitivity_algo"] == "Morris"
            or result.metadata.settings["sensitivity_algo"] == "MorrisAnalysis"
        ):
            figures["radar_plot"] = result.analysis.plot_radar(
                outputs=output_names,
                standardize=standardize,
                show=show,
                save=save,
                directory_path=directory_path,
            ).figures[0]
            figures["bar_plot"] = result.analysis.plot_bar(
                outputs=output_names,
                standardize=standardize,
                show=show,
                save=save,
                directory_path=directory_path,
                file_format="html",
                font_size=12,
            ).figures[0]

            final_names = []
            for name in output_names:
                if result.variable_dimensions[name] > 1:
                    final_names.extend(
                        (name, i) for i in range(result.variable_dimensions[name])
                    )
                else:
                    final_names.append(name)

            for name in final_names:
                figures["standard_plot"] = result.analysis.plot(
                    output=name,
                    show=show,
                    save=save,
                    file_path=directory_path / f"standard_plot_{name}",
                    file_format="png",
                )

        return figures
