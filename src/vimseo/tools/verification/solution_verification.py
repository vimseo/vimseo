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

r"""A tool to perform solution verification by estimating the discretization error.

Notation and uncertainty intervals are taken from
<https://asmedigitalcollection.asme.org/verification/article/7/3/031005/1146443/Confidence-Intervals-for-Richardson-Extrapolation>

Meshes $M_1$, $M_2$, $M_3$ are progressively refined meshes starting from a baseline
mesh $M_0$.
We define a relative element size, that is the element size divided by the largest one:
$\gamma = \frac{h(x)}{h_0(x)} < 1$
Note that $\gamma$ is independent on the location $x$ since all mesh elements are
assumed to be scaled by the same ratio for all x locations.

### The Relative Discretization Error (RDE)

From <https://www.sciencedirect.com/science/article/abs/pii/S0021999104004619>,

.. math::

  RDE_3 = \frac{q_{\gamma_3} - q_{exact}}{q_{exact}} = \frac{q_{\gamma_2} -
  q_{\gamma_1}}{q_{exact} ({\gamma}^{\beta} - 1)}

### Richardson extrapolation

Introduced by
[Richardson (1911)](https://doi.org/10.1098/rsta.1911.0009).

Considering $\gamma$ is a continuous variable, the true error on the simulation result
$q$ can be expanded in $\gamma$:

.. math::

  E_q(\gamma) = q_{exact} - q_{\gamma} \approx C {\gamma}^{\beta}

Then $\beta$ can be obtained from the non-linear equation:

.. math::

  \frac{E_{q,1}}{-{{\gamma}_2}^{\beta} + {{\gamma}_1}^{\beta}}
  = \frac{E_{q,2}}{-{{\gamma}_3}^{\beta} + {{\gamma}_2}^{\beta}}

with $E_{q,{\gamma}_j} = q_{{\gamma}_{j+1}} - q_{{\gamma}_{j}}$.

### Richardson-independent palliative estimates

The three-point Richardson extrapolation is fragile: its cross-validation returns
``nan`` as soon as one grid triplet is not cleanly power-law convergent, which
happens systematically for the sawtooth quantity but also for the smooth one on
sampled data. The tool therefore also reports two Richardson-independent estimates
of the converged value -- a least-squares power-law fit, whose order is fitted
rather than assumed, and a model-free median of the finest grids -- which stay
available in both cases. Their residual (fit) and band (median) quantify how
reliable the estimate is.

### Grid Convergence Index

.. math::

  GCI = F_s \frac{q_{\gamma_{i+1}} - q_{\gamma_i}}{q_{\gamma_{i+1}}} \frac{1}{(\gamma_i /
  \gamma_{i+1})^{\beta} - 1}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.mlearning.resampling import cross_validation
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import arange
from numpy import array
from numpy import full
from numpy import isnan
from numpy import vstack
from pandas import DataFrame
from pydantic import ConfigDict
from pydantic import Field
from strenum import StrEnum

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.model_metadata import MetaDataNames
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.doe.custom_doe import CustomDOESettings
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.post_tools.verification_plots import ConvergenceCrossValidation
from vimseo.tools.post_tools.verification_plots import ConvergenceFit
from vimseo.tools.post_tools.verification_plots import ErrorVersusElementSize
from vimseo.tools.post_tools.verification_plots import RelativeErrorVersusCpuTime
from vimseo.tools.post_tools.verification_plots import RelativeErrorVersusElementSize
from vimseo.tools.verification.base_verification import BaseVerification
from vimseo.tools.verification.solution_verification_indicators import compute_gci
from vimseo.tools.verification.solution_verification_indicators import compute_median
from vimseo.tools.verification.solution_verification_indicators import compute_rde
from vimseo.tools.verification.solution_verification_indicators import (
    compute_richardson,
)
from vimseo.tools.verification.solution_verification_indicators import (
    cross_validated_mad,
)
from vimseo.tools.verification.solution_verification_indicators import fit_power_law
from vimseo.tools.verification.solution_verification_indicators import (
    robust_converged_value,
)
from vimseo.tools.verification.verification_result import CASE_DESCRIPTION_TYPE
from vimseo.tools.verification.verification_result import SolutionVerificationResult
from vimseo.utilities.file_utils import camel_case_to_snake_case

if TYPE_CHECKING:
    from collections.abc import Mapping

    from plotly.graph_objs import Figure

LOGGER = logging.getLogger(__name__)


class Analysis(StrEnum):
    """The convergence analysis."""

    ELEMENT_SIZE = "ELEMENT_SIZE"
    """A convergence analysis versus the element size."""

    N_DOF = "N_DOF"
    """A convergence analysis versus the inverse of the number of degrees of freedom of
    the mesh."""


# TODO remove fields 'input_names' and 'output_names'
class SolutionVerificationSettings(CustomDOESettings):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    metric_names: list[str] = Field(
        default=["AbsoluteErrorMetric"],
        description="The name of the error metrics to compute.",
    )
    element_size_variable_name: str = Field(
        default="", description="The input variable name used as element size."
    )
    element_size_ratio: float | None = Field(
        default=None,
        description=r"The ratio between consecutive element sizes."
        r"If the default value of ``element_size_variable_name`` is "
        r":math:`dx_0`, then "
        r":math:`element_size_values= "
        r"[dx_0 \times r, dx_0, dx_0 \times r ^ {-1}, dx_0 \times r ^ {-2}] "
        r"with $r$ is the ``element_size_ratio``.",
    )
    element_size_values: list[float] = Field(
        default=[],
        description="The values of the element size. "
        "It must be a list with strictly decreasing values. "
        "If specified, it overrides the element size values generated from "
        "``element_size_ratio``.",
    )
    output_name: str = (
        Field(
            default="",
            description="The name of the output variable used to assess convergence.",
        ),
    )
    observed_output_names: list[str] = Field(
        default=[],
        description="A list of output names to be added as output of the verification."
        "These are just observed outputs, and do not modify the solution "
        "verification results."
        "If left to default value, observe all outputs except "
        "``MetaDataNames.error_code``, `job_directory`, "
        "`date`.",
    )
    analysis: Analysis = Field(
        default=Analysis.ELEMENT_SIZE,
        description="The type of convergence analysis. An analysis versus the element "
        "size is performed by default. If set to ``Analysis.N_DOF``, "
        "an analysis versus the number of degrees of freedom is performed. "
        "In this case, the ``element_size_variable_name`` should represent the "
        "number of degrees of freedom. The analysis is then performed against "
        "the inverse of the number of degrees of freedom.",
    )
    abscissa_name: str = Field(
        default="",
        description="The name of the variable versus which the convergence "
        "analysis is performed. If left to default value, the "
        "element_size_variable_name is used.",
    )
    simulated_data: Dataset | DataFrame | None = Field(
        default=None,
        description="The simulated data, containing the abscissa name "
        "and the output name.",
    )
    description: CASE_DESCRIPTION_TYPE | None = None


class StreamlitSolutionVerificationSettings(SolutionVerificationSettings):
    analysis: str = Analysis.ELEMENT_SIZE


class SolutionVerificationInputs(BaseInputs):
    model: IntegratedModel | None = None


class DiscretizationSolutionVerification(BaseVerification):
    """Assess discretization error of a model (solution verification).

    Analysis is based on model convergence along an element size parameter.
    """

    results: SolutionVerificationResult

    _INPUTS = SolutionVerificationInputs

    _SETTINGS = SolutionVerificationSettings

    _STREAMLIT_SETTINGS = StreamlitSolutionVerificationSettings

    _REFERENCE_PREFIX: ClassVar[str] = "Extrap"

    __NB_MESHES: ClassVar[int] = 4
    """The number of meshes simulated for the convergence analysis."""

    __FS: ClassVar[float] = 1.25
    """The safety factor on the Grid Convergence Index (GCI)."""

    _DOF_ABSCISSA_NAME = "N_dof_coarsest / N_dof"

    #: Name stored in ``extrapolation["q_converged_method"]`` for the reference
    #: (literature) Richardson extrapolation.
    _RICHARDSON_METHOD: ClassVar[str] = "richardson"
    #: Name flagging that the power-law-fit palliative was used instead of Richardson.
    _POWER_LAW_PALLIATIVE: ClassVar[str] = "power_law_fit (palliative)"
    #: Name flagging that the robust-median palliative was used instead of Richardson.
    _ROBUST_PALLIATIVE: ClassVar[str] = "robust_median (palliative)"

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        super().__init__(
            subtools=[CustomDOETool()],
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )
        self.result = SolutionVerificationResult()

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: SolutionVerificationInputs | None = None,
        settings: SolutionVerificationSettings | None = None,
        **options,
    ) -> SolutionVerificationResult:

        output_name = options["output_name"]
        model = options["model"]
        element_size_variable_name = options["element_size_variable_name"]

        self.result._fill_metadata(
            options["description"], options["model"].description if model else ""
        )
        self._output_names = [output_name]

        abscissa_name = (
            element_size_variable_name
            if options["abscissa_name"] == ""
            else options["abscissa_name"]
        )
        self.result.metadata.misc["element_size_variable_name"] = f"{abscissa_name}"

        if options["simulated_data"] is None:
            element_size_ratio = options["element_size_ratio"]
            if element_size_ratio is not None:
                dx_0 = model.default_input_data[element_size_variable_name]
                element_size_values = dx_0 * array([
                    element_size_ratio,
                    1.0,
                    element_size_ratio ** (-1),
                    element_size_ratio ** (-2),
                ])
            else:
                element_size_values = array(options["element_size_values"])

            input_dataset = Dataset.from_array(
                data=element_size_values,
                variable_names=[element_size_variable_name],
                variable_names_to_group_names={
                    element_size_variable_name: IODataset.INPUT_GROUP
                },
            )
            doe_tool = self._subtools["CustomDOETool"]
            metadata_variables_except_cpu_time = [
                var
                for var in model.get_metadata_names()
                if var != MetaDataNames.cpu_time
            ]
            if len(options["observed_output_names"]) > 0:
                output_names = options["observed_output_names"] + [
                    output_name,
                    MetaDataNames.cpu_time,
                ]
            else:
                output_names = [
                    name
                    for name in model.get_output_data_names()
                    if name not in metadata_variables_except_cpu_time
                ]
            doe_dataset = doe_tool.execute(
                model=model,
                input_dataset=input_dataset,
                output_names=output_names,
            ).dataset
            nb_meshes = self.__NB_MESHES
        else:
            doe_dataset = (
                options["simulated_data"]
                if isinstance(options["simulated_data"], Dataset)
                else Dataset.from_dataframe(options["simulated_data"])
            )
            element_size_values = (
                doe_dataset.get_view(variable_names=abscissa_name).to_numpy().ravel()
            )
            nb_meshes = len(element_size_values)

        h = doe_dataset.get_view(variable_names=abscissa_name).to_numpy().ravel()
        q = doe_dataset.get_view(variable_names=output_name).to_numpy().ravel()
        if options["analysis"] == Analysis.N_DOF:
            h = h[0] / h

        resampler = cross_validation.CrossValidation(
            arange(nb_meshes), n_folds=nb_meshes
        )
        # "fold_0" corresponds to the fold of the three finest meshes.
        cross_validation_result = {}
        for s in resampler.splits:
            # Example: "fold_0" uses the three finest grids [1, 2, 3].
            key = f"fold_{s.test[0]}"
            h_fold = h[s.train]
            q_fold = q[s.train]
            cross_validation_result[key] = {}
            cross_validation_result[key]["h"] = h_fold
            beta, q_extrap = compute_richardson(h_fold, q_fold)
            cross_validation_result[key]["beta"] = beta
            cross_validation_result[key]["q"] = q_fold
            cross_validation_result[key]["q_extrap"] = q_extrap

        q_extrap_array = array([
            cross_validation_result[key]["q_extrap"] for key in cross_validation_result
        ])
        # q[-1] is the solution on the finest grid.
        q_extrap_final, q_extrap_mad = compute_median(
            q_extrap_array, cross_validation_result["fold_0"]["q_extrap"]
        )

        beta_extrap_array = array([
            cross_validation_result[key]["beta"] for key in cross_validation_result
        ])
        beta_extrap_final, beta_extrap_mad = compute_median(
            beta_extrap_array, cross_validation_result["fold_0"]["beta"]
        )
        gci_fine, gci_fine_error_band = compute_gci(
            self.__FS, h, q, beta_extrap_final, nb_meshes - 2
        )
        gci_fine_1, gci_fine_1_error_band = compute_gci(
            self.__FS, h, q, 1, nb_meshes - 2
        )
        gci_fine_2, gci_fine_2_error_band = compute_gci(
            self.__FS, h, q, 2, nb_meshes - 2
        )
        gci_coarse, gci_coarse_error_band = compute_gci(
            self.__FS, h, q, beta_extrap_final, 0
        )
        gci_coarse_1, gci_coarse_1_error_band = compute_gci(self.__FS, h, q, 1, 0)
        gci_coarse_2, gci_coarse_2_error_band = compute_gci(self.__FS, h, q, 2, 0)
        extrapolation_result = {
            "beta": beta_extrap_final,
            "beta_mad": beta_extrap_mad,
            "q_extrap": q_extrap_final,
            "q_extrap_mad": q_extrap_mad,
            # GCI, from the two coarsest grids, and from the two finest.
            "gci": [gci_coarse, gci_fine],
            "gci_error_band": [gci_coarse_error_band, gci_fine_error_band],
            "gci_1": [gci_coarse_1, gci_fine_1],
            "gci_1_error_band": [gci_coarse_1_error_band, gci_fine_1_error_band],
            "gci_2": [gci_coarse_2, gci_fine_2],
            "gci_2_error_band": [gci_coarse_2_error_band, gci_fine_2_error_band],
            # Relative Discretization Error (Roy 2004), from coarse to fine grid.
            "rde": [
                compute_rde(self.__FS, h, q, q_extrap_final, beta, i)[0]
                for i in range(nb_meshes - 1)
            ][::-1],
            # RDE-based error band for the two coarsest grids.
            "rde_error_band": compute_rde(
                self.__FS, h, q, q_extrap_final, beta, nb_meshes - 2
            )[1],
        }

        # Richardson-independent *palliative* estimates of the converged solution.
        # Unlike the three-point Richardson extrapolation above, these never return
        # ``nan`` (they degrade gracefully on non-monotone / sawtooth convergence),
        # so a converged value and its uncertainty remain available when Richardson
        # fails. Their order is fitted, not assumed. See ``fit_power_law`` and
        # ``robust_converged_value``.
        q_converged_fit, order_fit, coefficient_fit, fit_rmse = fit_power_law(h, q)
        q_converged_robust, q_converged_robust_band = robust_converged_value(q)
        extrapolation_result["q_converged_fit"] = q_converged_fit
        extrapolation_result["order_fit"] = order_fit
        extrapolation_result["fit_coefficient"] = coefficient_fit
        extrapolation_result["fit_rmse"] = fit_rmse
        extrapolation_result["q_converged_robust"] = q_converged_robust
        extrapolation_result["q_converged_robust_band"] = q_converged_robust_band

        # Cross-validate the palliatives, but only when Richardson failed: each fold
        # (a leave-one-grid-out subset) yields a palliative converged value, and the
        # spread of the folds gives a cross-validation uncertainty band, consistent
        # with how Richardson is cross-validated above. The per-fold estimates are
        # stored alongside the Richardson ones so the cross-validation plot can show
        # them. Skipped when Richardson succeeds, since it is then the selected value.
        fit_cv_mad = float("nan")
        robust_cv_mad = float("nan")
        if isnan(q_extrap_final):
            fit_folds = []
            robust_folds = []
            for fold in cross_validation_result.values():
                fold_fit = fit_power_law(fold["h"], fold["q"])[0]
                fold_robust = robust_converged_value(fold["q"])[0]
                fold["q_converged_fit"] = fold_fit
                fold["q_converged_robust"] = fold_robust
                fit_folds.append(fold_fit)
                robust_folds.append(fold_robust)
            _, fit_cv_mad = cross_validated_mad(fit_folds)
            _, robust_cv_mad = cross_validated_mad(robust_folds)
        extrapolation_result["q_converged_fit_cv_mad"] = fit_cv_mad
        extrapolation_result["q_converged_robust_cv_mad"] = robust_cv_mad

        # Select the converged value: the Richardson extrapolation is the reference
        # (literature) method and is used whenever it is available; the palliatives
        # are only fallbacks when Richardson fails (``nan``). ``q_converged_method``
        # records which method was used and flags explicitly when a palliative was
        # substituted for Richardson. ``q_converged_cv_mad`` carries the matching
        # cross-validation uncertainty band (Richardson's MAD, or the palliative's).
        if not isnan(q_extrap_final):
            q_converged = q_extrap_final
            q_converged_method = self._RICHARDSON_METHOD
            q_converged_cv_mad = q_extrap_mad
        elif not isnan(q_converged_fit):
            q_converged = q_converged_fit
            q_converged_method = self._POWER_LAW_PALLIATIVE
            q_converged_cv_mad = fit_cv_mad
        else:
            q_converged = q_converged_robust
            q_converged_method = self._ROBUST_PALLIATIVE
            q_converged_cv_mad = robust_cv_mad
        extrapolation_result["q_converged"] = q_converged
        extrapolation_result["q_converged_method"] = q_converged_method
        extrapolation_result["q_converged_cv_mad"] = q_converged_cv_mad
        if q_converged_method != self._RICHARDSON_METHOD:
            LOGGER.warning(
                "Richardson extrapolation could not be computed (returned nan); "
                "falling back to the palliative '%s' for output '%s'. This is not "
                "the reference Richardson method.",
                q_converged_method,
                output_name,
            )

        # Create a ref dataset containing the selected converged value. Using
        # ``q_converged`` (Richardson when available, otherwise a palliative)
        # instead of ``q_extrap_final`` keeps the error metrics and the error /
        # relative-error plots populated even when Richardson returns nan.
        reference_data = Dataset.from_array(
            data=vstack([
                element_size_values,
                full((nb_meshes), q_converged),
            ]).T,
            variable_names=[
                abscissa_name,
                output_name,
            ],
            variable_names_to_group_names={
                abscissa_name: IODataset.INPUT_GROUP,
                output_name: IODataset.OUTPUT_GROUP,
            },
        )
        simulation_dataset = doe_dataset
        element_wise_metrics, integrated_metrics = self._compute_comparison(
            reference_data, simulation_dataset
        )

        simulation_and_reference, element_wise_metrics = self._post(
            simulation_dataset, reference_data, element_wise_metrics
        )
        if abscissa_name not in element_wise_metrics.get_variable_names(
            group_name=IODataset.INPUT_GROUP
        ):
            if options["analysis"] == Analysis.N_DOF:
                abscissa_name = self._DOF_ABSCISSA_NAME
            else:
                abscissa_name = f"Abscissa[{abscissa_name}]"
            element_wise_metrics.add_variable(
                variable_name=abscissa_name,
                data=h,
                group_name=IODataset.INPUT_GROUP,
            )

        self.result.simulation_and_reference = simulation_and_reference
        self.result.element_wise_metrics = element_wise_metrics
        self.result.integrated_metrics = integrated_metrics
        self.result.extrapolation = extrapolation_result
        self.result.cross_validation = cross_validation_result

        return self.result

    def plot_results(
        self,
        result: SolutionVerificationResult,
        save=False,
        show=True,
        directory_path: str | Path = "",
        file_format="html",
    ) -> Mapping[str, Figure]:
        """Superpose on a line plot the simulated output versus the element size, for all
        the cross validation folds. Secondly, plot in log-log the error of the output
        compared to the Richardson extrapolation, versus the element size.

        Args:
            result: The verification result to visualize.
            file_format: The format to which plots are generated.
        """
        figs = {}
        plots = [
            ConvergenceCrossValidation(),
            ConvergenceFit(),
            ErrorVersusElementSize(),
            RelativeErrorVersusElementSize(),
        ]
        if MetaDataNames.cpu_time in result.simulation_and_reference.get_variable_names(
            group_name=IODataset.OUTPUT_GROUP
        ):
            plots.append(RelativeErrorVersusCpuTime())

        for plot in plots:
            plot.working_directory = (
                self.working_directory if directory_path == "" else Path(directory_path)
            )
            figs[camel_case_to_snake_case(plot.__class__.__name__)] = plot.execute(
                result,
                show=show,
                save=save,
            ).figure
        return figs
