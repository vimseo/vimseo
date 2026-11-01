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
from typing import TYPE_CHECKING
from typing import Any

from gemseo.algos.doe.morris_doe.settings.morris_doe_settings import MorrisDOE_Settings
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.uncertainty import create_sensitivity_analysis
from gemseo.utils.directory_creator import DirectoryNamingMethod
from pydantic import Field

from vimseo.analysis_nodes.base_composite_analysis_node import BaseCompositeAnalysisNode
from vimseo.analysis_nodes.base_settings import BaseInputs
from vimseo.analysis_nodes.base_settings import BaseSettings
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.analysis_nodes.doe.doe import DOEInputs
from vimseo.analysis_nodes.doe.doe import DOESettings
from vimseo.analysis_nodes.doe.doe_result import DOEResult
from vimseo.analysis_nodes.sensitivity.doe_samples import UNSTRUCTURED_ALGO
from vimseo.analysis_nodes.sensitivity.doe_samples import check_no_nan_output
from vimseo.analysis_nodes.sensitivity.doe_samples import get_algo_settings
from vimseo.analysis_nodes.sensitivity.doe_samples import get_output_names
from vimseo.analysis_nodes.sensitivity.doe_samples import remove_nan_outputs
from vimseo.analysis_nodes.sensitivity.doe_samples import to_doe_result
from vimseo.analysis_nodes.sensitivity.doe_samples import to_io_dataset
from vimseo.analysis_nodes.sensitivity.sensitivity_result import SensitivityResult
from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


LOGGER = logging.getLogger(__name__)

_MORRIS_ALGORITHMS = ("Morris", "MorrisAnalysis")
"""The names of the Morris sensitivity analysis."""

_HSIC_ALGORITHMS = ("HSIC", "HSICAnalysis")
"""The names of the HSIC sensitivity analysis."""

_MORRIS_DOE_ALGORITHMS = ("MorrisDOE",)
"""The DOE algorithms suitable for the Morris sensitivity analysis."""

_HSIC_DOE_ALGORITHMS = (
    "OT_MONTE_CARLO",
    "OT_RANDOM",
    "MC",
    "OT_LHS",
    "PYDOE_LHS",
    "LHS",
    UNSTRUCTURED_ALGO,
)
"""The DOE algorithms suitable for the HSIC sensitivity analysis.

They generate independent samples distributed according to the probability
distribution of the inputs, i.e. a Monte Carlo sampling
or a Latin Hypercube Sampling (LHS) that is not optimized;
the samples of :data:`.UNSTRUCTURED_ALGO` are assumed to be so."""

_LHS_SETTINGS_TO_DEFAULTS = {
    "PYDOE_LHS": {"criterion": None},
    "LHS": {"optimization": None, "strength": 1},
}
"""The settings of the LHS algorithms that make them optimized or structured,
with their values for a plain LHS, suitable for the HSIC sensitivity analysis."""

_MORRIS_STEP = 0.05
"""The relative step of the Morris DOE, as the default one of GEMSEO."""


def _check_plain_lhs(doe_result: DOEResult, algo_settings: Mapping[str, Any]) -> None:
    """Check that the LHS of a HSIC analysis is not optimized.

    An optimized LHS spreads its samples, which are then not independent.

    Args:
        doe_result: The result of the DOE.
        algo_settings: The settings of the DOE algorithm.

    Raises:
        ValueError: When the LHS is optimized.
    """
    algo_name = doe_result.metadata.settings.get("algo")
    for name, default in _LHS_SETTINGS_TO_DEFAULTS.get(algo_name, {}).items():
        value = algo_settings.get(name, default)
        # The settings may be enumerations, e.g. Criterion.maximin.
        value = getattr(value, "value", value)
        if value != default:
            msg = (
                "The sensitivity analysis 'HSIC' requires a Latin Hypercube Sampling "
                f"that is not optimized, whereas the setting {name!r} of {algo_name!r} "
                f"is {value!r}."
            )
            raise ValueError(msg)


def _check_morris_samples(dataset: Dataset) -> None:
    """Check that the samples of a Morris DOE are complete.

    Each sample is used by position in its trajectory,
    so a missing sample or a NaN output, e.g. a failed evaluation, is not allowed.

    Args:
        dataset: The samples of the Morris DOE.

    Raises:
        ValueError: When a sample is missing or has a NaN output.
    """
    dimension = dataset.group_names_to_n_components[dataset.INPUT_GROUP]
    if not len(dataset) or len(dataset) % (dimension + 1):
        msg = (
            f"The Morris DOE has {len(dataset)} samples, whereas its "
            f"trajectories have {dimension + 1} samples each; "
            "an evaluation of the model may have failed."
        )
        raise ValueError(msg)

    check_no_nan_output(dataset, "Morris")


class SensitivityAnalysisNodeSettings_(BaseSettings):
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


class SensitivityAnalysisNodeSettings(SensitivityAnalysisNodeSettings_):
    """The sensitivity settings."""


class StreamlitSensitivityAnalysisNodeSettings(SensitivityAnalysisNodeSettings_):
    """The sensitivity settings for the workflow dashboard."""


class SensitivityAnalysisNodeInputs(BaseInputs):
    parameter_space: ParameterSpace = ParameterSpace()
    model: IntegratedModel | None = None
    doe_result: DOEResult | None = Field(
        default=None,
        description="The result of a DOE prepared in advance, e.g. by a DOEAnalysisNode. "
        "For the Morris analysis, "
        "it must be generated by the DOE algorithm 'MorrisDOE'. "
        "For the HSIC analysis, "
        "the samples must be independent and distributed "
        "according to the probability distribution of the parameter space, "
        "i.e. generated by a Monte Carlo sampling "
        "('OT_MONTE_CARLO', 'OT_RANDOM' or 'MC') "
        "or by a Latin Hypercube Sampling that is not optimized "
        "('OT_LHS', 'PYDOE_LHS' or 'LHS'); "
        "an optimized Latin Hypercube Sampling or a quasi Monte Carlo sequence "
        "is not suitable. "
        "If ``None``, sample the model over the parameter space. "
        "The Morris analysis rejects a missing sample or a NaN output, "
        "e.g. a failed evaluation of the model, "
        "whereas the HSIC analysis removes the samples with a NaN output.",
    )
    dataset: Dataset | None = Field(
        default=None,
        description="Samples not generated by a DOE, "
        "e.g. measurements or runs searched in an archive, "
        "with an input group and an output group. "
        "For the HSIC analysis only: "
        "the samples must be independent and distributed "
        "according to the probability distribution of the inputs, "
        "which cannot be checked. "
        "They are wrapped into a DOE result whose DOE algorithm is "
        f"{UNSTRUCTURED_ALGO!r}. "
        "Cannot be used together with ``doe_result``.",
    )


class SensitivityAnalysisNode(BaseCompositeAnalysisNode):
    """Run a sensitivity analysis on the outputs of an :class:`~.IntegratedModel` over a
    :class:`~.gemseo.algos.parameter_space.ParameterSpace`."""

    result: SensitivityResult

    _INPUTS = SensitivityAnalysisNodeInputs

    _SETTINGS = SensitivityAnalysisNodeSettings

    _STREAMLIT_SETTINGS = StreamlitSensitivityAnalysisNodeSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            sub_analysis_nodes=[DOEAnalysisNode()],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            **options,
        )
        self.result = SensitivityResult()

    @BaseCompositeAnalysisNode._validate
    def execute(
        self,
        inputs: SensitivityAnalysisNodeInputs = None,
        settings: SensitivityAnalysisNodeSettings = None,
        **options,
    ) -> SensitivityResult:
        model = options["model"]
        algo = options["sensitivity_algo"]
        is_morris = algo in _MORRIS_ALGORITHMS
        if not is_morris and algo not in _HSIC_ALGORITHMS:
            msg = f"{algo} is not handled."
            raise ValueError(msg)

        if model is not None:
            self.result.metadata.model = model.description

        doe_result = options["doe_result"]
        samples = options["dataset"]
        if samples is not None:
            if doe_result is not None:
                msg = "A DOE result and a dataset cannot be provided together."
                raise ValueError(msg)

            LOGGER.warning(
                "The samples of the dataset are assumed to be independent and "
                "distributed according to the probability distribution of the inputs, "
                "which cannot be checked."
            )
            doe_result = to_doe_result(samples)

        if doe_result is None:
            if model is None:
                msg = "Either a model or the result of a DOE must be provided."
                raise ValueError(msg)

            doe_result = self.__execute_doe(model, is_morris, options)
        else:
            self._sub_analysis_nodes["DOEAnalysisNode"].result = doe_result

        algo_settings = get_algo_settings(
            doe_result,
            _MORRIS_DOE_ALGORITHMS if is_morris else _HSIC_DOE_ALGORITHMS,
            algo,
        )
        if not is_morris:
            _check_plain_lhs(doe_result, algo_settings)

        doe_dataset = doe_result.dataset
        output_names = get_output_names(doe_dataset, options["output_names"])
        dataset = to_io_dataset(doe_dataset, output_names)
        if is_morris:
            _check_morris_samples(dataset)
            # Set like MorrisAnalysis.compute_samples does.
            dataset.misc["step"] = MorrisDOE_Settings(**algo_settings).step
            # Used by MorrisAnalysis to normalize its indices.
            dataset.misc["outputs_bounds"] = {
                name: (data.min(0), data.max(0))
                for name, data in dataset.output_dataset.to_dict_of_arrays(
                    by_group=False
                ).items()
            }
        else:
            remove_nan_outputs(dataset)

        self.result.metadata.report["doe_dataset_name"] = doe_dataset.name
        self.result.analysis = create_sensitivity_analysis(
            analysis=algo, samples=dataset
        )

        self.result.metadata.report["output_names"] = output_names
        self.result.indices = self.result.analysis.compute_indices()
        n_components = self.result.analysis.dataset.variable_names_to_n_components
        self.result.variable_dimensions = {
            name: n_components[name]
            for name in [*self.result.analysis.input_names, *output_names]
        }
        return self.result

    def __execute_doe(
        self, model: IntegratedModel, is_morris: bool, options: Mapping[str, Any]
    ) -> DOEResult:
        """Execute the DOE suitable for the sensitivity analysis.

        Args:
            model: The model.
            is_morris: Whether the sensitivity analysis is a Morris one.
            options: The options of the analysis node.

        Returns:
            The result of the DOE.

        Raises:
            ValueError: When the number of samples of a HSIC analysis is zero.
        """
        parameter_space = options["parameter_space"]
        n_samples = options["n_samples"]
        if is_morris:
            algo = "MorrisDOE"
            n_samples = n_samples or options["n_replicates"] * (
                parameter_space.dimension + 1
            )
            algo_settings = {"step": _MORRIS_STEP}
        else:
            if n_samples == 0:
                msg = "The HSIC analysis requires a number of samples."
                raise ValueError(msg)

            algo = "OT_MONTE_CARLO"
            algo_settings = {}

        return self._sub_analysis_nodes["DOEAnalysisNode"].execute(
            inputs=DOEInputs(model=model, parameter_space=parameter_space),
            settings=DOESettings(
                output_names=options["output_names"]
                or model.get_output_data_names(remove_metadata=True),
                algo=algo,
                n_samples=n_samples,
                algo_settings=algo_settings,
            ),
        )
