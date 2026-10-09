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
from typing import Annotated
from typing import Any

from emcee import EnsembleSampler
from gemseo.datasets.dataset import Dataset
from gemseo.mlearning.transformers.scaler.min_max_scaler import MinMaxScaler
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import append
from numpy import array
from numpy import asarray
from numpy import delete
from numpy import exp
from numpy import floor
from numpy import inf
from numpy import isfinite
from numpy import isnan
from numpy import log
from numpy import mean
from numpy import ndarray
from numpy import ones
from numpy import random
from numpy import std
from numpy import sum as np_sum
from numpy import vstack
from numpy import zeros
from openturns import ComposedDistribution
from openturns import DeconditionedDistribution
from openturns import DistributionImplementation
from openturns import Normal
from openturns import RandomGenerator
from openturns import Sample
from openturns import SymbolicFunction
from openturns import TruncatedDistribution
from openturns import UserDefined
from openturns import dist
from pandas import DataFrame
from pydantic import BeforeValidator
from pydantic import ConfigDict
from pydantic import Field
from pydantic import SkipValidation

from vimseo.config.global_configuration import _configuration as config
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.bayes.bayes_analysis_result import BayesAnalysisResult
from vimseo.utilities.datasets import to_dataset

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


random.seed(1)  # ruff: ignore[numpy-legacy-random]
RandomGenerator.SetSeed(0)  # ruff: ignore[numpy-legacy-random]
LOGGER = logging.getLogger(__name__)


class BayesSettings(BaseSettings):
    """The settings of a Bayes analysis.

    Examples:
        # Prior distributions for parameters of a Normal model: mean and
        standard deviation.
        >>> from openturns import Uniform
        >>> from openturns import ComposedDistribution
        # The prior distribution can be defined as a list of independant marginals:
        >>> prior_1 = [Uniform(0, 3), Uniform(1, 3)]
        # Or through an OpenTurns ``ComposedDistribution```.
        # In this case, the marginals can be supposed independent:
        >>> prior_2 = ComposedDistribution([Uniform(0, 3), Uniform(1, 3)])
        # Or correlated:
        >>> from openturns import CorrelationMatrix
        >>> from openturns import NormalCopula
        >>> R = CorrelationMatrix(2)
        >>> R[0, 1] = -0.25
        >>> prior_3 = ComposedDistribution([Uniform(0, 3), Uniform(1, 3)], NormalCopula(R))
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    likelihood_dist: str = Field(
        default="",
        description="The name of the probabilistic model to be calibrated. "
        "Should be an OpenTURNS model. `Access the OpenTURNS documentation"
        "<http://openturns.github.io/openturns/latest/user_manual/"
        "probabilistic_modelling.html>`_.",
    )
    prior_dist: Annotated[
        ComposedDistribution | list[DistributionImplementation], SkipValidation
    ] = Field(
        default=[],
        description="The prior distribution. Either a list of openturns distribution "
        "or a composed distribution.",
    )
    frozen_variables: dict[str, list[int | float]] = Field(
        default={},
        description="The frozen variables. Examples: "
        "- {'free_index': [0], 'frozen_index': [1], 'frozen_values': [0.1]}, "
        "- {'frozen_index': [1], 'frozen_values': [0.1]}",
    )


def _coerce_to_sample(data: Any) -> Any:
    """Convert user data to the 1-D sample of a single scalar variable.

    Args:
        data: The data to convert, either a mapping, a DataFrame or a Dataset holding a
            single scalar variable, or a sequence of values.

    Returns:
        The data as a 1-D array when it can be converted, and unchanged otherwise.

    Raises:
        ValueError: When the data hold several variables or a vector variable.
    """
    if isinstance(data, (Dataset, DataFrame, Mapping)):
        dataset = to_dataset(data)
        if dataset.shape[1] != 1:
            msg = (
                "The data of a Bayes analysis must hold a single scalar variable, "
                f"got the variables {dataset.variable_names} with "
                f"{dataset.shape[1]} components; select the variable to calibrate on."
            )
            raise ValueError(msg)
        return dataset.to_numpy().ravel()

    if isinstance(data, (list, tuple)):
        return asarray(data, dtype=float)

    return data


class BayesInputs(BaseInputs):
    """The inputs of a Bayes analysis."""

    data: Annotated[ndarray, BeforeValidator(_coerce_to_sample)] = Field(
        default=array([]),
        description="The data from which the inference is carried out: "
        "the sample of a single scalar variable, as an array, a list, "
        "a mapping such as ``{'young_modulus': [...]}``, a DataFrame or a Dataset.",
    )
    x0s: ndarray = Field(
        default=array([]),
        description="The starting points of the algorithm. "
        "In practice a 1-D array of size the number "
        "of parameters of the model.",
    )
    n_mcmc: int = Field(
        default=1_000, description="The number of steps of the mcmc analysis."
    )

    n_walkers: int = Field(default=30, description="The number of walkers.")


class BayesTool(BaseAnalysisTool):
    """Run a Bayesian calibration of a probabilistic model."""

    _SETTINGS = BayesSettings

    _INPUTS = BayesInputs

    _x0s: ndarray
    """The starting points of the MCMC algorithm."""

    _frozen_options: dict
    """The options to set values if necessary."""

    _dist_model: DistributionImplementation
    """The probabilistic model to calibrate."""

    _dist_prior: DistributionImplementation
    """The prior distribution on the model parameters."""

    _scaler: MinMaxScaler
    """The scaler of the variables."""

    _log_posterior: Callable
    """The log-posterior function."""

    _log_likelihood: Callable
    """The log-likelihood function."""

    _log_prior: Callable
    """The log-prior function."""

    data: Sample
    """The log-prior function."""

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

        self.result = BayesAnalysisResult()

    def _log_likelihood(self, x: ndarray, data: Sample) -> float:
        """Return the value of the log-likelihood for candidate model parameters.

        Args:
            x: The candidate model parameters.
            data: The data used in the inference process.

        Returns: The value of the joint log-likelihood.
        """

        if self._frozen_options == {}:
            self._dist_model.setParameter(x)

        else:
            x_eff = zeros(
                max(
                    append(
                        self._frozen_options["frozen_index"],
                        self._frozen_options["free_index"],
                    )
                )
                + 1
            )

            x_eff[self._frozen_options["frozen_index"]] = self._frozen_options[
                "frozen_values"
            ]

            x_eff[self._frozen_options["free_index"]] = x

            self._dist_model.setParameter(x_eff)

        return np_sum(array(self._dist_model.computeLogPDF(data)))

    def _log_prior(self, x: array) -> float:
        """Return the value of the log-prior for candidate model parameters.

        Args:
            x: The candidate model parameters.

        Returns: The value of the joint log-prior.
        """

        return self._dist_prior.computeLogPDF(x)

    def log_posterior(
        self,
        x: ndarray,
        func_prior: Callable,
        func_likelihood: Callable,
    ):
        """Return the value of the log-posterior for candidate model parameters.

        Args:
            x: The candidate model parameters.
            func_prior: The log-prior function.
            func_likelihood: The log-likelihood function.

        Returns: The value of the log-posterior.
        """
        x_r = self._scaler.inverse_transform(x)

        lp = func_prior(x_r)

        if not isfinite(lp):
            return -inf

        lik = func_likelihood(x_r)

        if not isfinite(lik):
            return -inf

        return lik + lp

    def sampling(
        self,
        n_mcmc: int,
        data: ndarray,
    ):
        """Return the raw MCMC posterior samples .

        Args:
            n_mcmc: The number of MCMC iterations.
            data: The data to condition the model parameters.

        Returns: The raw MCMC samples before thinning and burn-in.
        """

        likelihood_function = lambda x: self._log_likelihood(x, data)  # ruff: ignore[lambda-assignment]

        prior_function = lambda x: self._log_prior(x)  # ruff: ignore[lambda-assignment]

        log_posterior = lambda x: self.log_posterior(  # ruff: ignore[lambda-assignment]
            x, prior_function, likelihood_function
        )

        sampler = EnsembleSampler(
            len(self._x0s), self._dist_prior.getDimension(), log_posterior
        )

        sampler.run_mcmc(self._x0s, n_mcmc, progress=True)

        return self._scaler.inverse_transform(sampler.get_chain())

    @BaseTool.validate
    def execute(
        self,
        inputs: BayesInputs | None = None,
        settings: BayesSettings | None = None,
        **options,
    ) -> BayesAnalysisResult:
        """Samples the posterior distribution of the parameters of model conditionnally
        to data and to a prior distribution.

        This class works only for data directly measured (no inverse method required).
        """

        if options["likelihood_dist"] == "":
            msg = "The probabilistic model is not specified."

            raise ValueError(msg)

        if options["prior_dist"] == []:
            msg = "The prior model is not specified."

            raise ValueError(msg)

        if options["data"].size == 0:
            msg = "There is no data to calibrate the model."

            raise ValueError(msg)

        self._data = Sample(options["data"].reshape(-1, 1))
        self.result.data = options["data"]

        self._dist_model = getattr(dist, options["likelihood_dist"])()

        self._dist_prior = (
            ComposedDistribution(options["prior_dist"])
            if isinstance(options["prior_dist"], list)
            else options["prior_dist"]
        )

        list_marginals = [
            self._dist_prior.getMarginal(i).getName()
            for i in range(self._dist_prior.getDimension())
        ]

        if list_marginals.__contains__("Dirac"):
            msg = (
                "A prior model with Dirac distributions raises numerical errors."
                " Use rather `frozen_options` to fix variables."
            )

            raise ValueError(msg)

        self._scaler = MinMaxScaler()

        self._frozen_options = options["frozen_variables"]

        dim = self._dist_prior.getDimension()

        eff_dim = dim

        if options["frozen_variables"] != {}:
            free_index = [
                i
                for i in range(self._dist_model.getParameterDimension())
                if not self._frozen_options["frozen_index"].__contains__(i)
            ]

            self._frozen_options["free_index"] = free_index

            eff_dim = dim + len(self._frozen_options["frozen_index"])

        bounds = vstack((
            array(self._dist_prior.getRange().getLowerBound()),
            array(self._dist_prior.getRange().getUpperBound()),
        ))

        if self._dist_model.getParameterDimension() != eff_dim:
            msg = (
                "The number of model parameters is not compatible"
                " with the dimension of the prior."
            )

            raise ValueError(msg)

        self._x0s = (
            0.5 * ones(dim) + 1e-4 * random.randn(options["n_walkers"], dim)  # ruff: ignore[numpy-legacy-random]
            if options["x0s"].size == 0
            else options["x0s"] * (1 + 1e-4 * random.randn(options["n_walkers"], dim))  # ruff: ignore[numpy-legacy-random]
        )

        self._scaler.fit(bounds)

        raw_samples = self.sampling(
            options["n_mcmc"],
            self._data,
        )

        self.result.raw_samples = raw_samples

        self.result.thin_number = len(self._x0s)

        self.result.ndim = dim

        parameter_names = list(self._dist_model.getParameterDescription())
        if self._frozen_options:
            parameter_names = [
                parameter_names[i] for i in self._frozen_options["free_index"]
            ]
        self.result.parameter_names = tuple(parameter_names)

        return self.result

    def cropping(self, samples: array, thin: int, burnin: int, dim: int) -> array:
        """Post-process the posterior samples to keep the relevant data.

        Args:
            samples: The raw MCMC samples.`
            thin: the thinning parameter.
            burnin: the number of initial samples to be discarded.
            dim: the number of model parameters: The plot of the raw MCMC chains.

        Returns: The cropped MCMC posterior samples.
        """

        nb_samples = int(floor((samples.shape[0] - burnin) / thin))

        if nb_samples == 0:
            msg = "Not enough MCMC samples have been generated."

            raise ValueError(msg)

        filtered_samples = zeros((nb_samples, thin, dim))

        for j in range(filtered_samples.shape[0]):
            filtered_samples[j, :, :] = samples[burnin + thin * j - 1, :, :]

        return filtered_samples.reshape(int(nb_samples * thin), dim)

    def build_posterior_predictive(
        self,
        nb_samples: int,
    ) -> DeconditionedDistribution:
        """Builds the posterior predictive distribution.

        Args:
            nb_samples: The number of posterior samples
            to build the posterior predictive distribution.
            Should be less than 2000 due to very large consumption
            and long computational time.

        Returns: The posterior predictive distribution
        that makes prediction according to the probabilistic model.
        """

        if nb_samples < 500:
            LOGGER.warning(
                "A minimum of posterior samples of samples "
                "is recommended to ensure convergence."
            )

        elif nb_samples > 2000:
            msg = (
                "The construction of the posterior predictive distribution "
                "is limited to 2000 due to very large consumption "
                "and long computational time."
            )

            raise ValueError(msg)

        censored_samples = self.result.processed_samples[
            : min(nb_samples, len(self.result.processed_samples)), :
        ]

        effective_samples = censored_samples

        if self._frozen_options != {}:
            n = (
                max(
                    append(
                        self._frozen_options["frozen_index"],
                        self._frozen_options["free_index"],
                    )
                )
                + 1
            )

            s, k = 0, 0

            effective_samples = zeros((len(censored_samples), int(n)))

            for i in range(n):
                if self._frozen_options["frozen_index"].__contains__(i):
                    effective_samples[:, i] = self._frozen_options["frozen_values"][
                        k
                    ] * ones(len(effective_samples))

                    k += 1

                else:
                    effective_samples[:, i] = censored_samples[:, s]

                    s += 1

        link_function = SymbolicFunction(
            [f"p{k}" for k in range(effective_samples.shape[1])],
            [f"p{k}" for k in range(effective_samples.shape[1])],
        )

        empirical_posterior = UserDefined(
            Sample(effective_samples),
            1 / len(effective_samples) * ones(len(effective_samples)),
        )

        return DeconditionedDistribution(
            self._dist_model, empirical_posterior, link_function
        )

    def marginal_likelihood(self, nb_samples: int) -> float:
        """Compute a verification criterion, the marginal likelihood.

        Args:
            nb_samples: The number of Monte Carlo samples
            to compute the marginal likelihood.

        Returns: Twice the opposite of the log marginal likelihood.
        """

        LOGGER.warning(
            "Make sure enough samples are generated to draw "
            "reliable conclusions from the criterion (at least 10000)"
        )

        list_instrumental = [
            TruncatedDistribution(
                Normal(
                    mean(self.result.processed_samples[:, j]),
                    std(self.result.processed_samples[:, j]),
                ),
                self._dist_prior.getRange().getLowerBound()[j],
                self._dist_prior.getRange().getUpperBound()[j],
            )
            for j in range(self.result.ndim)
        ]

        dist_instrumental = ComposedDistribution(list_instrumental)

        samples_mc = dist_instrumental.getSample(nb_samples)

        val_prior = self._log_prior(samples_mc)

        val_likelihood = array([
            self._log_likelihood(samples_mc[j, :], data=self._data)
            for j in range(nb_samples)
        ])

        idx = ~isnan(val_likelihood)

        val_inst = dist_instrumental.computeLogPDF(samples_mc)[idx]

        return -2 * log(mean(exp(val_likelihood[idx] + val_prior[idx] - val_inst)))

    # TODO: generalize to enable cross-validation

    def lppd(self, burnin: int, n_mcmc: int) -> float:
        """Compute a verification criterion, the log-pointwise prediction.

        Args:
            burnin: The number of initial samples to be discarded.
            n_mcmc: The number of MCMC iterations.

        Returns: Twice the opposite of the log pointwise prediction density.
        """

        LOGGER.warning(
            "Make sure enough samples are generated to draw "
            "reliable conclusions from the criterion (at least 10000)"
        )

        vect_values = zeros(len(self._data))

        for k in range(len(self._data)):
            data_censored = Sample(delete(array(self._data).ravel(), k).reshape(-1, 1))

            mcmc_samples = self.sampling(n_mcmc, data_censored)

            samples_leave_k = self.cropping(
                mcmc_samples, len(self._x0s), burnin, self.result.ndim
            )

            log_k = zeros(len(samples_leave_k))

            for j in range(len(samples_leave_k)):
                log_k[j] = self._log_likelihood(samples_leave_k[j, :], self._data[k])

            nan_index = ~isnan(log_k)

            vect_values[k] = mean(exp(log_k[nan_index]))

        return -2 * np_sum(log(vect_values))

    def post(
        self,
        burnin: int,
        n_mcmc: int = 1_000,
        nb_samples_ml: int = 10_000,
        nb_samples_posterior: int = 100,
    ) -> BayesAnalysisResult:
        """Performs the full post-processing tasks.

        Args:
            burnin: The number of initial samples to be discarded.
            n_mcmc: The number of MCMC iterations for the lppd.
            nb_samples_ml: The number of Monte Carlo samples
            to compute the marginal likelihood.
            nb_samples_posterior: The number of posterior samples
            to build the posterior predictive distribution.
            Should be less than 2000 due to very large consumption
            and long computational time.

        The result is published again in the archive of the tool results,
        since it was published at the end of :meth:`execute`, before this
        post-processing.

        Returns: The result of the Bayesian inference.
        """
        self.result.metadata.misc["post"] = {
            "burnin": burnin,
            "n_mcmc": n_mcmc,
            "nb_samples_ml": nb_samples_ml,
            "nb_samples_posterior": nb_samples_posterior,
        }
        self.result.processed_samples = self.cropping(
            self.result.raw_samples, self.result.thin_number, burnin, self.result.ndim
        )

        self.result.posterior_predictive = self.build_posterior_predictive(
            nb_samples_posterior
        )

        self.result.lppd = self.lppd(burnin, n_mcmc)

        self.result.ml = self.marginal_likelihood(nb_samples_ml)

        self._republish_result()
        return self.result
