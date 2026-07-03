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

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from emcee import EnsembleSampler
from gemseo.mlearning.transformers.scaler.min_max_scaler import MinMaxScaler
from gemseo.utils.directory_creator import DirectoryNamingMethod
from gemseo.utils.matplotlib_figure import save_show_figure
from matplotlib.pyplot import subplots
from numpy import append
from numpy import array
from numpy import delete
from numpy import empty
from numpy import exp
from numpy import floor
from numpy import inf
from numpy import isfinite
from numpy import isnan
from numpy import linspace
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
from pydantic import ConfigDict
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.bayes.bayes_analysis_result import BayesAnalysisResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    from matplotlib.pyplot import Axes
    from matplotlib.pyplot import Figure

random.seed(1)  # noqa: NPY002
RandomGenerator.SetSeed(0)  # noqa: NPY002
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
    prior_dist: ComposedDistribution | list[DistributionImplementation] = Field(
        default=[],
        description="The prior distribution. Either a list of openturns distribution.",
    )
    frozen_variables: dict = Field(
        default={},
        description="The frozen variables",
    )


class BayesInputs(BaseInputs):
    """The inputs of a Bayes analysis."""

    data: ndarray = Field(
        default=empty(0),
        description="The data from which the inference is carried out.",
    )
    x0s: ndarray = Field(
        default=empty(0),
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

    def _log_likelihood(self, x: array, data: Sample) -> float:
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

        likelihood_function = lambda x: self._log_likelihood(x, data)  # noqa: E731

        prior_function = lambda x: self._log_prior(x)  # noqa: E731

        log_posterior = lambda x: self.log_posterior(  # noqa: E731
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

        if len(options["data"]) == 0:
            msg = "There is no data to calibrate the model."

            raise ValueError(msg)

        self._data = Sample(options["data"].reshape(-1, 1))

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
            0.5 * ones(dim) + 1e-4 * random.randn(options["n_walkers"], dim)  # noqa: NPY002
            if len(options["x0s"]) == 0
            else options["x0s"] * (1 + 1e-4 * random.randn(options["n_walkers"], dim))  # noqa: NPY002
        )

        self._scaler.fit(bounds)

        raw_samples = self.sampling(
            options["n_mcmc"],
            self._data,
        )

        self.result.raw_samples = raw_samples

        self.result.thin_number = len(self._x0s)

        self.result.ndim = dim

        return self.result

    def plot_burnin(
        self,
        result: BayesAnalysisResult,
        directory_path: str | Path = "",
        save=False,
        show=True,
    ) -> Figure:
        """Plot the MCMC chains to determine the burn-in.

        Args:
            result: The result of :meth:`~bayes.bayes_analysis.execute`.
            directory_path: where to save the plot.

        Returns: The plot of the raw MCMC chains.
        """
        directory_path = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )

        parameters_name = self._dist_model.getParameterDescription()

        fig, axes = subplots(result.ndim, sharex=True)
        for i in range(result.ndim):
            ax = axes[i]
            ax.plot(result.raw_samples[:, :, i], "k", alpha=0.3)
            ax.set_xlim(0, len(result.raw_samples))
            ax.yaxis.set_label_coords(-0.1, 0.5)
            ax.set_ylabel(parameters_name[i])

        axes[-1].set_xlabel("step number")

        save_show_figure(fig, show, directory_path / "raw_mcmc.png" if save else "")

        return fig

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

        Returns: Twice the opposite of the log pointwise prediction density.
        """
        self.result.processed_samples = self.cropping(
            self.result.raw_samples, self.result.thin_number, burnin, self.result.ndim
        )

        self.result.posterior_predictive = self.build_posterior_predictive(
            nb_samples_posterior
        )

        self.result.lppd = self.lppd(burnin, n_mcmc)

        self.result.ml = self.marginal_likelihood(nb_samples_ml)

        return self.result

    def plot_posterior_distribution(
        self,
        result: BayesAnalysisResult,
        directory_path: str | Path = "",
        save=False,
        show=True,
    ) -> Figure:
        """Plot the posterior distribution.

        Args:
            directory_path: Where to save the plot.
            result: The result of :meth:`~bayes.bayes_analysis.execute`.

        Returns: The plot of the posterior distribution.
        """

        ndim = result.ndim

        parameters_name = self._dist_model.getParameterDescription()

        fig, axes = subplots(ndim, ndim)

        for i in range(ndim):
            for j in range(ndim):
                if i == j:
                    axes[i, i].hist(result.processed_samples[:, i])

                    axes[i, i].set_xlabel(parameters_name[i])

                elif i > j:
                    axes[i, j].scatter(
                        result.processed_samples[:, i], result.processed_samples[:, j]
                    )

                    axes[i, j].set_xlabel(parameters_name[i])
                    axes[i, j].set_ylabel(parameters_name[j])

                else:
                    axes[i, j].set_axis_off()

        Path(directory_path).mkdir(parents=True, exist_ok=True)
        save_show_figure(
            fig,
            show,
            directory_path / "posterior_distribution.png" if save else "",
        )

        return fig

    def plot_predictive_distribution(
        self,
        n_disc: int,
        name: str,
        directory_path: str | Path = "",
        save: bool = False,
        show: bool = False,
        **kwargs,
    ) -> Axes:
        """Plot the posterior predictive distribution.

        Args:
            kwargs: A dictionnary for plot options.
            n_disc: The discretization of the input variable.
            name: The name of the input variable.
            directory_path: Where to save the plot.

        Returns: The plot of the posterior predictive distribution.
        """
        x_disc = linspace(
            0.1 * min(array(self._data).ravel()),
            2 * max(array(self._data).ravel()),
            num=n_disc,
        )

        fig, ax = subplots()

        ax1 = ax.twinx()
        ax.hist(array(self._data).ravel(), label="Experimental data")
        ax1.plot(
            x_disc,
            self.result.posterior_predictive.computePDF(Sample(x_disc.reshape(-1, 1)))
            / max(
                array(
                    self.result.posterior_predictive.computePDF(
                        Sample(x_disc.reshape(-1, 1))
                    )
                )
            ),
            label="posterior predictive distribution for "
            + self._dist_model.getName()
            + " model.",
            **kwargs,
        )
        ax1.set_ylabel("PDF")
        ax1.set_xlabel(name)
        ax1.legend()

        if save and directory_path == "":
            msg = "There is no directory path provided."

            raise ValueError(msg)

        Path(directory_path).mkdir(parents=True, exist_ok=True)
        save_show_figure(
            fig, show, directory_path / "posterior_predictive.png" if save else ""
        )

        return ax, ax1

    def plot_results(
        self,
        n_disc: int = 100,
        name: str = "",
        directory_path: str | Path = "",
        save: bool = False,
        show: bool = True,
        **kwargs,
    ) -> Mapping[str, Figure]:
        """Generate the different plots.

        Args:
            kwargs: a dictionary for plot options.
            n_disc: The discretization of the input.`
            name: The name of the input variable.`
            directory_path: where to save the plot.

        Returns: The plot of the cropped MCMC chains
        and the posterior predictive distribution
        that makes prediction according to the probabilistic model.
        """
        directory_path = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )

        figs = {}

        figs["posterior_samples"] = self.plot_posterior_distribution(
            self.result, directory_path, save, show
        )

        figs["posterior_predictive"] = self.plot_predictive_distribution(
            n_disc, name, directory_path, save, show, **kwargs
        )

        return figs
