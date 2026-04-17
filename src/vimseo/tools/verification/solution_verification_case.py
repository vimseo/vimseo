# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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

"""A tool to compare several solution verifications."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from gemseo.datasets.dataset import Dataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import array
from pandas import DataFrame
from pydantic import ConfigDict
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.verification_case_plots import ConvergenceCase
from vimseo.tools.post_tools.verification_case_plots import CpuTimeCompromiseCase
from vimseo.tools.verification.verification_result import SolutionVerificationCaseResult
from vimseo.tools.verification.verification_result import SolutionVerificationResult

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from plotly.graph_objs import Figure


class SolutionVerificationCaseSettings(BaseSettings):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    results: Dataset | list[SolutionVerificationResult] = Field(
        default=[], description="Solution verification results."
    )

    # TODO to be removed. It is to make sure Dataset is imported.
    dummy: Dataset | None = None


class SolutionVerificationCase(BaseAnalysisTool):
    """Assess discretization error of a model (solution verification).

    Analysis is based on model convergence along an element size parameter.
    """

    results: SolutionVerificationCaseResult

    _SETTINGS = SolutionVerificationCaseSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )
        self.result = SolutionVerificationCaseResult()

    @BaseTool.validate
    def execute(
        self,
        settings: SolutionVerificationCaseSettings | None = None,
        **options,
    ) -> SolutionVerificationCaseResult:

        # TODO get settings of the results, check that some are constant for all results.
        result_0 = options["results"][0]
        settings = result_0["metadata"]["settings"]
        elt_size_var_name = result_0["metadata"]["misc"]["element_size_variable_name"]
        self.result.metadata.misc.update(settings)
        self.result.metadata.misc["element_size_variable_name"] = elt_size_var_name
        self.result.metadata.misc["nb_meshes"] = len(
            result_0["simulation_and_reference"]
        )
        self.result.metadata.misc["variable_names"] = result_0[
            "simulation_and_reference"
        ].variable_names

        extrapolated_values_folds = []
        simulated_values = defaultdict(list)

        for result in options["results"]:
            variable_names = result["simulation_and_reference"].variable_names
            extrapolated_values_folds += [
                cross_validation["q_extrap"]
                for cross_validation in result["cross_validation"].values()
            ]
            for name in variable_names:
                simulated_values[name] += list(
                    result["simulation_and_reference"]
                    .get_view(variable_names=name)
                    .to_numpy()
                    .ravel()
                )

        data = {"extrapolated_values_folds": array(extrapolated_values_folds).flatten()}
        for name in variable_names:
            data.update({name: array(simulated_values[name]).flatten()})
        df = DataFrame.from_dict(data)

        self.result.convergence_data = df

        return self.result

    def plot_results(
        self,
        result: SolutionVerificationCaseResult,
        output_name: str = "",
        normalize_index_output: int | None = None,
        dark_mode: bool = False,
        directory_path: str | Path = "",
        save=False,
        show=True,
    ) -> Mapping[str, Figure]:
        """Superpose several convergence trajectories and CPU time versus the output
        variable of interest.

        Args:
            result: The verification result to visualize.
            output_name: The name of the output variable on which convergence is studied.
            The output name stores as setting in the passed convergence result
            is used by default.
            normalize_index_output: The index of the CPU time (x-axis of the plot)
            used to normalize the output of interest. It means that the output
            of interest for each convergence trajectories is equal to one
            at this location.
            normalize_index_cpu_time: The index of the CPU time (x-axis of the plot)
            used to normalize the CPU time values. It means that the CPU time
            for each convergence trajectories is equal to one at this location.
            dark_mode: Whether to use dark mode for the plots.
        """
        figs = {}
        figs["convergence"] = ConvergenceCase(
            working_directory=directory_path
            if directory_path != ""
            else self.working_directory
        ).execute(
            result.convergence_data,
            result.metadata.misc["nb_meshes"],
            result.metadata.misc["element_size_variable_name"],
            (result.metadata.misc["output_name"] if output_name == "" else output_name),
            normalize_index_output=normalize_index_output,
            hovering_variables=result.metadata.misc["variable_names"],
            dark_mode=dark_mode,
            save=save,
            show=show,
        )

        figs["cpu_time_compromise"] = CpuTimeCompromiseCase(
            working_directory=directory_path
            if directory_path != ""
            else self.working_directory
        ).execute(
            result.convergence_data,
            result.metadata.misc["nb_meshes"],
            result.metadata.misc["element_size_variable_name"],
            (result.metadata.misc["output_name"] if output_name == "" else output_name),
            normalize_index_output=normalize_index_output,
            hovering_variables=result.metadata.misc["variable_names"],
            dark_mode=dark_mode,
            save=save,
            show=show,
        )

        return figs
