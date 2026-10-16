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

from copy import deepcopy
from typing import TYPE_CHECKING
from typing import Any

from gemseo import create_scenario
from gemseo.algos.doe.base_doe_settings import BaseDOESettings
from gemseo.algos.doe.factory import DOELibraryFactory
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
    from collections.abc import Mapping
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


def _get_settings_class(algo_name: str) -> type[BaseDOESettings]:
    """Return the class of the settings of a DOE algorithm.

    Args:
        algo_name: The name of the DOE algorithm.

    Returns:
        The class of the settings.
    """
    library = DOELibraryFactory().create(algo_name)
    return library.ALGORITHM_INFOS[algo_name].Settings


def _validate_algo_settings(
    algo_name: str, algo_settings: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the settings of a DOE algorithm.

    Args:
        algo_name: The name of the DOE algorithm.
        algo_settings: The settings passed to the DOE algorithm.

    Returns:
        The settings specific to the DOE algorithm, with their default values,
        and the generic settings of a DOE that are passed,
        as the DOE algorithm reads them.
    """
    settings_class = _get_settings_class(algo_name)
    names = set(settings_class.model_fields).difference(BaseDOESettings.model_fields)
    # The callables are not serializable.
    names.update(set(algo_settings).difference(("callbacks", "preprocessors")))
    return settings_class(**algo_settings).model_dump(include=names)


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
    algo_settings: dict[str, Any] = Field(
        default={},
        description="The settings of the DOE algo, other than the number of samples "
        "(see gemseo.get_algorithm_options_schema(algo)). "
        "The metadata of the result store them as validated by the DOE algo, "
        "with the default values of the settings specific to this algo.",
    )


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
        self.__algo_settings = {}
        """The validated settings of the DOE algorithm of the last execution."""

    @BaseTool.validate
    def execute(
        self,
        inputs: DOEInputs | None = None,
        settings: DOESettings | None = None,
        **options,
    ) -> DOEResult:
        model = options["model"]
        algo_settings = dict(options["algo_settings"])
        # Some DOE algorithms, e.g. the ones of the OAT methods,
        # derive their number of samples from their other settings.
        doe_name = f"DOE_{model.name}_{model.load_case.name}_{options['algo']}"
        if "n_samples" in _get_settings_class(options["algo"]).model_fields:
            algo_settings["n_samples"] = options["n_samples"]
            doe_name = f"{doe_name}_{options['n_samples']}"

        self.__algo_settings = _validate_algo_settings(options["algo"], algo_settings)
        output_names = _set_output_names(model, options["output_names"])

        doe_scenario = create_scenario(
            disciplines=[model],
            formulation_name="DisciplinaryOpt",
            objective_name=output_names[0],
            # A DOE sets the current value of the variables to its best sample,
            # which is meaningless for an evaluation of the model.
            design_space=deepcopy(options["parameter_space"]),
            name=doe_name,
            scenario_type="DOE",
        )
        if len(output_names) > 1:
            for out_name in output_names[1:]:
                doe_scenario.add_observable(out_name)

        doe_scenario.execute(algo_name=options["algo"], **algo_settings)

        self.result.dataset = doe_scenario.formulation.optimization_problem.to_dataset(
            name=doe_name, categorize=True, opt_naming=False
        )

        return self.result

    def _set_options_to_results(self, options):
        super()._set_options_to_results(options)
        self.result.metadata.settings["algo_settings"] = self.__algo_settings
