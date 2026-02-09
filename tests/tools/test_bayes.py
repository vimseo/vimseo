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

import re

import pytest
from matplotlib.figure import Figure
from matplotlib.pyplot import Axes
from numpy import array
from numpy import inf
from numpy import log
from numpy import max as np_max
from numpy import min as np_min
from numpy import random
from numpy import zeros
from numpy.testing import assert_array_equal
from openturns import ComposedDistribution
from openturns import Dirac
from openturns import Uniform
from sqlalchemy.cyextension.util import Mapping

from vimseo.tools.bayes.bayes_analysis import BayesTool

random.seed(1)  # noqa: NPY002


@pytest.fixture(scope="module")
def data() -> array:
    """The dataset used to calibrate the probabilistic model."""
    return random.randn(10) + 2  # noqa: NPY002


@pytest.fixture(scope="module")
def model() -> str:
    """A probabilistic model to calibrate."""
    return "Normal"


@pytest.fixture(scope="module")
def prior() -> array:
    """A prior for the model parameters."""
    return ComposedDistribution([Uniform(0, 5)] * 2)


@pytest.fixture(scope="module")
def bayes_analysis(model, prior, data) -> BayesTool:
    """A raw MCMC sampling."""
    analysis = BayesTool()
    analysis.execute(likelihood_dist=model, prior_dist=prior, data=data, n_mcmc=50)
    return analysis


@pytest.fixture(scope="module")
def processed_analysis(bayes_analysis) -> BayesTool:
    """A MCMC chain."""
    bayes_analysis.post(
        1,
        n_mcmc=50,
        nb_samples_ml=5,
        nb_samples_posterior=2,
    )
    return bayes_analysis


def test_missing_likelihood(tmp_wd):
    """Check an error is raised if no model is defined."""
    analysis = BayesTool()
    with pytest.raises(
        ValueError,
        match=re.escape("The probabilistic model is not specified."),
    ):
        analysis.execute()


def test_missing_prior(tmp_wd, model):
    """Check an error is raised if no prior is defined."""
    analysis = BayesTool()
    with pytest.raises(
        ValueError,
        match=re.escape("The prior model is not specified."),
    ):
        analysis.execute(likelihood_dist=model)


def test_dirac_prior(tmp_wd, model, data):
    """Check an error is raised if Dirac distributions are used for priors."""
    analysis = BayesTool()
    with pytest.raises(
        ValueError,
        match=re.escape(
            "A prior model with Dirac distributions raises numerical errors."
            " Use rather `frozen_options` to fix variables."
        ),
    ):
        analysis.execute(
            likelihood_dist=model,
            data=data,
            prior_dist=[Uniform(), Dirac(0.1)],
            n_mcmc=2,
        )


def test_missing_data(tmp_wd, model, prior):
    """Check an error is raised if no prior is available."""
    analysis = BayesTool()
    with pytest.raises(
        ValueError,
        match=re.escape("There is no data to calibrate the model."),
    ):
        analysis.execute(likelihood_dist=model, prior_dist=prior)


def test_no_correspondance_prior_likelihood(tmp_wd, prior, data):
    """Check that the dimension of the prior corresponds to the number of model
    parameters."""
    analysis = BayesTool()
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The number of model parameters is not compatible"
            " with the dimension of the prior."
        ),
    ):
        analysis.execute(likelihood_dist="WeibullMin", prior_dist=prior, data=data)


def test_execution_settings(tmp_wd, model, prior, data):
    """Check the initialization settings of a mock inference ."""
    analysis = BayesTool()
    analysis.execute(likelihood_dist=model, prior_dist=prior, data=data, n_mcmc=10)

    assert analysis.result.ndim == 2
    assert analysis.result.thin_number == 30
    assert analysis._frozen_options == {}
    assert_array_equal(data, array(analysis._data).ravel())


@pytest.mark.parametrize(
    (
        "prior",
        "expected_value_in",
        "candidate_in",
        "candidate_out",
        "frozen_args",
        "expected_frozen",
        "dim",
    ),
    [
        (
            [Uniform(0, 5), Uniform(0, 5)],
            log(0.04),
            array([0.5, 0.5]),
            array([-0.2, 0.2]),
            {},
            {},
            2,
        ),
        (
            ComposedDistribution([Uniform(0, 5)] * 2),
            log(0.04),
            array([0.5, 0.5]),
            array([-0.2, 0.2]),
            {},
            {},
            2,
        ),
        (
            ComposedDistribution([Uniform(0, 5)]),
            log(0.2),
            array([0.5]),
            array([-0.2]),
            {"frozen_index": [1], "frozen_values": [0.1]},
            {"free_index": [0], "frozen_index": [1], "frozen_values": [0.1]},
            1,
        ),
    ],
)
def test_instanciation_prior(
    tmp_wd,
    model,
    data,
    prior,
    expected_value_in,
    candidate_in,
    candidate_out,
    frozen_args,
    expected_frozen,
    dim,
):
    """Check the different ways to assign the prior."""
    analysis = BayesTool()
    analysis.execute(
        likelihood_dist=model,
        prior_dist=prior,
        data=data,
        n_mcmc=2,
        frozen_variables=frozen_args,
    )
    assert analysis.result.ndim == dim
    assert analysis._dist_prior.computeLogPDF(candidate_in) == expected_value_in
    assert analysis._dist_prior.computeLogPDF(candidate_out) == -inf
    assert analysis._frozen_options == expected_frozen
    assert analysis.result.raw_samples.shape[2] == dim


def test_return_type(tmp_wd, bayes_analysis):
    """Check the return type of plot_burnin."""
    assert isinstance(
        bayes_analysis.plot_burnin(result=bayes_analysis.result, show=False), Figure
    )


def test_execution_results(tmp_wd, processed_analysis):
    """Check the results of an inference."""
    assert processed_analysis.result.processed_samples.shape == (30, 2)
    assert processed_analysis.result.raw_samples.shape == (50, 30, 2)
    censored_samples = array(
        processed_analysis.result.posterior_predictive.getConditioningDistribution().getParameter()
    )
    assert (
        int(censored_samples.shape[0] / (processed_analysis.result.ndim + 1)) <= 2_000
    )
    assert (
        np_min(processed_analysis.result.raw_samples[:, :, 0])
        > processed_analysis._dist_prior.getRange().getLowerBound()[0]
    )
    assert (
        np_min(processed_analysis.result.raw_samples[:, :, 1])
        > processed_analysis._dist_prior.getRange().getLowerBound()[1]
    )
    assert (
        np_max(processed_analysis.result.raw_samples[:, :, 0])
        < processed_analysis._dist_prior.getRange().getUpperBound()[0]
    )
    assert (
        np_max(processed_analysis.result.raw_samples[:, :, 1])
        < processed_analysis._dist_prior.getRange().getUpperBound()[1]
    )

    attributes = dir(processed_analysis.result)
    assert "lppd" in attributes
    assert "ml" in attributes


def test_error_cropping(tmp_wd, bayes_analysis):
    """Check that an error is raised when not enough samples are generated."""
    mock_samples = zeros((10, 30, 2))
    with pytest.raises(
        ValueError,
        match=re.escape("Not enough MCMC samples have been generated."),
    ):
        bayes_analysis.cropping(mock_samples, thin=30, burnin=1, dim=2)


def test_lppd(tmp_wd, bayes_analysis):
    """Check the returned lppd."""
    assert bayes_analysis.lppd(burnin=1, n_mcmc=40) > 0


def test_marginal_likelihood(tmp_wd, processed_analysis):
    """Check the returned marginal likelihood."""
    assert processed_analysis.marginal_likelihood(10) > 0


def test_maximum_size_posterior_predictive(tmp_wd, processed_analysis):
    """Check the maximum size of posterior samples for the function."""
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The construction of the posterior predictive distribution "
            "is limited to 2000 due to very large consumption and long computational "
            "time."
        ),
    ):
        processed_analysis.build_posterior_predictive(2001)


def test_plot_posterior_predictive(tmp_wd, processed_analysis):
    """Check that error is raised when no path is provided."""

    with pytest.raises(
        ValueError,
        match=re.escape("There is no directory path provided."),
    ):
        processed_analysis.plot_predictive_distribution(
            name="X", n_disc=200, save=True, show=False
        )


@pytest.mark.parametrize("plot_directory", ["", "foo"])
def test_plot_results_return_type(tmp_wd, model, prior, data, plot_directory):
    """Check that plot_results output is a dictionary."""
    analysis = BayesTool()
    analysis.execute(likelihood_dist=model, prior_dist=prior, data=data, n_mcmc=50)
    analysis.post(
        1,
        n_mcmc=50,
        nb_samples_ml=5,
        nb_samples_posterior=2,
    )
    assert analysis.working_directory.absolute().exists()
    plot_checks = analysis.plot_results(
        directory_path=plot_directory, save=True, show=False
    )
    assert isinstance(plot_checks, Mapping)
    assert "posterior_samples" in plot_checks
    assert "posterior_predictive" in plot_checks
    assert isinstance(plot_checks["posterior_samples"], Figure)
    for fig in plot_checks["posterior_predictive"]:
        assert isinstance(fig, Axes)


def test_plot_posterior_distributio_return_type(tmp_wd, processed_analysis):
    """Check that plot_posterior_distribution output is a figure."""
    assert isinstance(
        processed_analysis.plot_posterior_distribution(
            processed_analysis.result, show=False
        ),
        Figure,
    )


def test_plot_predictive_distribution_return_type(tmp_wd, processed_analysis):
    """Check that plot_predictive_distribution output is a figure."""
    res_plot = processed_analysis.plot_predictive_distribution(
        name="X", n_disc=200, show=False
    )
    assert isinstance(res_plot[0], Axes)
    assert isinstance(res_plot[1], Axes)
