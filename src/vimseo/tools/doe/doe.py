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

# Copyright (c) 2022 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Jorge CAMACHO-CASERO, Ludovic BARRIERE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from gemseo import create_scenario
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.utils.directory_creator import DirectoryNamingMethod
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.doe.doe_result import DOEResult

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _set_output_names(
    model: IntegratedModel, output_names: Sequence[str]
) -> Sequence[str]:
    if output_names:
        if not set(output_names).issubset(model.output_grammar.names):
            msg = (
                f"Elements of {output_names} are not included in the outputs "
                f"of the model, which are "
                f"{model.output_grammar.names}"
            )
            raise ValueError(msg)
        return output_names
    return list(model.output_grammar.names)


# TODO update from gemseo once branch pydantic is integrated (v6)
class DOESettings(BaseSettings):
    output_names: list[str] = Field(
        default=[],
        description="The names of the output variables computed by the model.",
    )
    n_samples: int = Field(default=10, description="The number of samples of the DOE.")
    algo: str = Field(
        default="OT_OPT_LHS",
        description="The name of the DOE algo. "
        "See from gemseo.api.get_available_doe_algorithms().",
    )
    # algo_options: dict | None = Field(
    #     default=None,
    #     description="The options of the DOE algo "
    #     "(See gemseo.api.get_algorithm_options_schema(algo)).",
    # )


class DOEInputs(BaseInputs):
    model: IntegratedModel | None = None
    parameter_space: ParameterSpace = ParameterSpace()


class StreamlitDOESettings(DOESettings):
    # algo_options: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        self.algo = None if self.algo == "" else self.algo
        # self.algo_options = None if self.algo == {} else self.algo_options


class DOETool(BaseAnalysisTool):
    """Run a DOE executing an :class:`~.IntegratedModel` over a
    :class:`~.gemseo.algos.parameter_space.ParameterSpace`."""

    results: DOEResult
    """The results of a :class:`~.DOETool`."""

    _INPUTS = DOEInputs

    _SETTINGS = DOESettings

    _STREAMLIT_SETTINGS = StreamlitDOESettings

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
        self.result = DOEResult()

    @BaseTool.validate
    def execute(
        self,
        inputs: DOEInputs | None = None,
        settings: DOESettings | None = None,
        **options,
    ) -> DOEResult:
        model = options["model"]
        doe_name = (
            f"DOE_{model.name}_{model.load_case.name}_{options['algo']}_"
            f"{options['n_samples']}"
        )

        output_names = _set_output_names(model, options["output_names"])

        doe_scenario = create_scenario(
            disciplines=[model],
            formulation_name="DisciplinaryOpt",
            objective_name=output_names[0],
            design_space=options["parameter_space"],
            name=doe_name,
            scenario_type="DOE",
        )
        if len(output_names) > 1:
            for out_name in output_names[1:]:
                doe_scenario.add_observable(out_name)

        doe_scenario.execute(
            algo_name=options["algo"],
            n_samples=options["n_samples"],
        )

        self.result.dataset = doe_scenario.formulation.optimization_problem.to_dataset(
            name=doe_name, categorize=True, opt_naming=False
        )

        return self.result
