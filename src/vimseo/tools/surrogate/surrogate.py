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
from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any

from gemseo import BaseRegressor
from gemseo import create_surrogate
from gemseo.datasets.dataset import Dataset
from gemseo.disciplines.surrogate import SurrogateDiscipline
from gemseo.mlearning.core.quality.base_ml_algo_quality import BaseMLAlgoQuality
from gemseo.mlearning.core.quality.factory import MLAlgoQualityFactory
from gemseo.mlearning.core.selection import MLAlgoSelection
from gemseo.post.mlearning.ml_regressor_quality_viewer import MLRegressorQualityViewer
from gemseo.utils.directory_creator import DirectoryNamingMethod
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.surrogate.surrogate_result import SurrogateResult

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from plotly.graph_objects import Figure

    from vimseo.tools.surrogate.surrogate_result import QualitiesType

LOGGER = logging.getLogger(__name__)

KFOLDS = BaseMLAlgoQuality.EvaluationMethod.KFOLDS
LEARN = BaseMLAlgoQuality.EvaluationMethod.LEARN
LOO = BaseMLAlgoQuality.EvaluationMethod.LOO
BOOTSTRAP = BaseMLAlgoQuality.EvaluationMethod.BOOTSTRAP

CandidateType = Mapping[str, Mapping[str, Any]]

MEASURE_EVALUTATION_METHOD_NAMES = {
    KFOLDS: "compute_cross_validation_measure",
    LEARN: "compute_learning_measure",
    LOO: "compute_leave_one_out_measure",
    BOOTSTRAP: "compute_bootstrap_measure",
}


class SurrogateInputs(BaseInputs):
    model: IntegratedModel | None = None
    dataset: Dataset | None = None


class SurrogateSettings(BaseSettings):
    plot: str = "PredictionVsTrue"
    algo: str = Field(
        default="",
        description="The name of the surrogate algorithm to use. "
        "If None, a selection will "
        "be made among candidate algorithms (candidates can be defined in "
        ":meth:`.__init__()` or :meth:`set_candidates()`. by default "
        ":attr:`.DEFAULT_CANDIDATES` is used).",
    )
    algo_options: dict = Field(
        default={},
        description=" Dictionary of options for the surrogate algorithm. "
        "If None, default options are used.",
    )
    candidates: CandidateType = Field(
        default={
            "RBFRegressor": {
                "smooth": [0, 0.01, 0.1, 1, 10, 100],
                "transformer": [dict(BaseRegressor.DEFAULT_TRANSFORMER)],
            },
            "LinearRegressor": {"fit_intercept": [True, False]},
            "PolynomialRegressor": {
                "degree": [1, 2, 3],
                "fit_intercept": [True, False],
            },
            "GaussianProcessRegressor": {
                "transformer": [dict(BaseRegressor.DEFAULT_TRANSFORMER)]
            },
        },
        description="The candidate surrogates.",
    )
    quality_measures: list[str] = Field(
        default=["MSEMeasure"], description="The measure of quality to compute."
    )
    evaluation_methods: list[str] = Field(
        default=[
            KFOLDS,
            LEARN,
        ],
        description="The evaluation methods to use.",
    )
    evaluation_options: dict[str, dict] = Field(
        default={
            KFOLDS: {"n_folds": 5},
            LOO: {"samples": None},
            LEARN: {"samples": None},
            BOOTSTRAP: {"n_replicates": 100, "samples": None},
        },
        description="The options of the evaluation methods.",
    )
    quality_for_selection: list[str] = Field(
        default=(
            "MSEMeasure",
            KFOLDS,
        ),
        description="The quality measures to use.",
    )
    output_names: list[str] = Field(
        default=[],
        description="List of output names that will be approximated by the "
        "surrogate model. If None, all the outputs are considered.",
    )


class SurrogateTool(BaseAnalysisTool):
    results: SurrogateResult

    _INPUTS = SurrogateInputs

    _SETTINGS = SurrogateSettings

    QUALITY_FACTORY = MLAlgoQualityFactory()

    DEFAULT_PLOT = "PredictionVsTrue"

    _selector: MLAlgoSelection
    """Select the best candidate."""

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
        self.result = SurrogateResult()
        self.__load_case = None
        self._selector = None

    def add_candidate(self, candidate: CandidateType) -> None:
        """
        Append candidate to the list of candidates
        Args:
            candidate: new candidate to add to the current option

        """
        candidates = self._options["candidates"]
        candidates.update(candidate)
        self.update_options(candidates=candidates)

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: SurrogateInputs | None = None,
        settings: SurrogateSettings | None = None,
        **options,
    ) -> SurrogateResult:
        """Builds surrogate model(s) according to the result of sampling of the original
        model contained in ``dataset``."""

        # TODO: manage dimension reduction for outputs with sizes >1 by checking
        #  dimension of outputs (from model or dataset?) and adding a transformer.
        algo = options["algo"]
        model = options["model"]
        self.__load_case = model.load_case.name

        if algo:  # no selection
            self.result.model_name = f"{model.name}.{self.__load_case}.{algo}"
            LOGGER.info(f"Creating surrogate model: {self.result.model_name}")

            self.result.model = create_surrogate(
                surrogate=algo,
                data=options["dataset"],
                disc_name=self.result.model_name,
                output_names=options["output_names"],
                **options["algo_options"],
            )

        else:  # selection
            LOGGER.info(
                f"Selecting best surrogate model for {model.name} and load case "
                f"{self.__load_case}"
            )
            eval_method = options["quality_for_selection"][1]
            self._selector = MLAlgoSelection(
                options["dataset"],
                measure=options["quality_for_selection"][0],
                measure_evaluation_method_name=eval_method,
                **options["evaluation_options"][eval_method],
            )
            for candidate_name, candidate in options["candidates"].items():
                self._selector.add_candidate(
                    candidate_name, calib_algo=None, calib_space=None, **candidate
                )

            best_algo = self._selector.select()
            self.result.model_name = (
                f"{model.name}.{self.__load_case}.{best_algo.__class__.__name__}"
            )
            self.result.model = SurrogateDiscipline(
                best_algo,
                disc_name=self.result.model_name,
                output_names=options["output_names"],
            )

            self.result.selection_qualities = self.compute_selection_qualities()

        self.result.qualities = self.__compute_quality(
            self.result.model.regression_model
        )

        return self.result

    @property
    def selected_algo(self):
        return self.result.model.regression_model

    def __compute_quality(self, candidate):

        quality = {}
        for qual_mes in self._options["quality_measures"]:
            measure = self.QUALITY_FACTORY.create(
                qual_mes,
                algo=candidate,
            )
            quality[qual_mes] = {}
            for eval_meth in self._options["evaluation_methods"]:
                quality[qual_mes][eval_meth] = getattr(
                    measure, MEASURE_EVALUTATION_METHOD_NAMES[eval_meth]
                )(**self._options["evaluation_options"][eval_meth])

        return quality

    # def compute_quality(
    #     self,
    #     quality_measures: Iterable[str] | None = None,
    #     eval_methods: Iterable[str] | None = None,
    #     eval_options: Mapping[str : Mapping[str, Any]] | None = None,
    # ) -> Mapping[str : type(BaseMLAlgoQuality)]:
    #     """Computes a set of quality measures for the current surrogate model.
    #
    #     Args:
    #         quality_measures: List of quality measures to evaluate
    #         eval_methods: List of evaluation methods to evaluate the measure
    #         eval_options: Dictionary of options for evaluation methods
    #
    #     Returns:
    #         Dictionary of quality measures associated to evaluation methods.
    #     """
    #     if quality_measures:
    #         self.update_options(quality_measures=quality_measures)
    #     if eval_options:
    #         self.update_options(evaluation_options=eval_options)
    #     if eval_methods:
    #         self.update_options(evaluation_methods=eval_methods)
    #
    #     quality = {}
    #     for qual_mes in self._options["quality_measures"]:
    #         measure = self.QUALITY_FACTORY.create(
    #             qual_mes, algo=self.result.model.regression_model
    #         )
    #         quality[qual_mes] = {}
    #         for eval_meth in self._options["evaluation_methods"]:
    #             quality[qual_mes][eval_meth] = getattr(
    #                 measure, MEASURE_EVALUTATION_METHOD_NAMES[eval_meth]
    #             )(**self._options["evaluation_options"][eval_meth])
    #
    #     return quality

    @property
    def quality(self) -> QualitiesType:
        return self.result.qualities

    def compute_selection_qualities(
        self,
        quality_measures: Iterable[str] | None = None,
        eval_methods: Iterable[str] | None = None,
        eval_options: Mapping[str : Mapping[str, Any]] | None = None,
    ) -> Mapping[str : Mapping[str : Mapping[str : type(BaseMLAlgoQuality)]]]:
        """Computes the quality measures of the candidate algorithms (selected in
        :meth:`execute`).

        Args:
            quality_measures: List of quality measures to evaluate
            eval_methods: List of evaluation methods to evaluate the measure
            eval_options: Dictionary of options for evaluation methods

        Returns:
            Dictionary of quality measures and their evaluations through evaluation
            methods for each candidate.
        """
        candidate_qualities = {}

        if quality_measures:
            self.update_options(quality_measures=quality_measures)
        if eval_options:
            self.update_options(evaluation_options=eval_options)
        if eval_methods:
            self.update_options(evaluation_methods=eval_methods)

        if self._selector:
            for candidate in self._selector.candidates:
                cand_name = candidate[0].__class__.__name__
                # candidate_qualities[cand_name] = {}
                candidate_qualities[cand_name] = self.__compute_quality(candidate[0])
                # for qual_mes in self._options["quality_measures"]:
                #     measure = self.QUALITY_FACTORY.create(qual_mes, algo=candidate[0])
                #     candidate_qualities[cand_name][qual_mes] = {}
                #     for eval_meth in self._options["evaluation_methods"]:
                #         candidate_qualities[cand_name][qual_mes][eval_meth] = getattr(
                #             measure, MEASURE_EVALUTATION_METHOD_NAMES[eval_meth]
                #         )(**self._options["evaluation_options"][eval_meth])
        else:
            LOGGER.info(
                "No selection of surrogate models available. "
                "Requires a run of the :meth:`!SurrogateTool.execute()` method"
            )

        return candidate_qualities

    def plot_results(
        self,
        result: SurrogateResult,
        output_names: Iterable[str] = (),
        directory_path: str | Path = "",
        show: bool = True,
        save: bool = False,
        **options,
    ) -> Mapping[str, Figure]:
        """Plotting the results according to a specific plot.

        Args:
            output_names: The names of the outputs for which cross-validation is plotted.
                If left to default value, all model output names are considered.
        """

        options.update({"show": show, "save": save})
        if not output_names:
            output_names = result.model.output_grammar.names

        # TODO activate cross validation mode when available in GEMSEO.
        # TODO add directory_path=self.working_directory when discrimination
        #  of Dataset constructor and execute options is done.
        viewer = MLRegressorQualityViewer(result.model.regression_model)

        figures = {}
        for output_name in output_names:
            file_name = f"surrogate_{result.model.name}_learning_{output_name}"
            figures.update({
                file_name: viewer.plot_predictions_vs_observations(
                    output_name,
                    save=save,
                    show=show,
                    file_name=file_name,
                ).figures[0]
            })

        return figures
