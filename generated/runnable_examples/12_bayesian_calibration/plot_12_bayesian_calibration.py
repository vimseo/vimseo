# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This work is licensed under a BSD 0-Clause License.
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
# FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Usage of Bayesian inference
==============================

The :class:`~.BayesTool` provides methods to perform the calibration
under uncertainties of a model.
"""

# %%
from __future__ import annotations

from gemseo.datasets.dataset import Dataset
from numpy import random
from openturns import ComposedDistribution
from openturns import Uniform
from strenum import StrEnum

from vimseo.api import activate_logger
from vimseo.tools.bayes.bayes_analysis import BayesTool
from vimseo.tools.bayes.bayes_analysis_result import PosteriorChecks
from vimseo.tools.statistics.statistics_tool import StatisticsTool

random.seed(0)  # noqa: NPY002

activate_logger()

N_MCMC = 100

# %%
# 1) Set-up of the stochastic model
# ==================================
# We start loading the experimental data
# that will be processed to calibrate models:
data_modulus = random.logistic(150000, 8000, 8)  # noqa: NPY002


# %%
# We want to calibrate several probabilistic models,
# that is to say probability distributions,
# for instance Normal, Weibull, Log-normal:
class Models(StrEnum):
    NORMAL = "Normal"
    WEIBULL_MIN = "WeibullMin"
    LOG_NORMAL = "LogNormal"


analysis_n = BayesTool(working_directory="normal_model")
analysis_l = BayesTool(working_directory="lognormal_model")
analysis_w = BayesTool(working_directory="weibullmin_model")

# %%
# For each model,
# it is necessary to define a prior.
# Except for the Normal model,
# it is difficult to give an initial guess
# for the Weibull and Lognormal model.
# To achieve this goal,
# we compute the frequentist estimates
# of the model parameters.
# The result of the frequentist estimate for the Normal model:
statistic_tool = StatisticsTool()
dataset = Dataset.from_array(data_modulus.reshape(-1, 1))
results_normal = statistic_tool.execute(
    dataset=dataset, tested_distributions=["Normal"]
)

# %%
# From this result, we set-up the prior:
prior_normal = ComposedDistribution([Uniform(110000, 160000), Uniform(2000, 12000)])

# %%
# Similarly for the Weibull Min model:
# the frequentist estimate:
results_weibull = statistic_tool.execute(
    dataset=dataset, tested_distributions=["WeibullMin"]
)

# %%
# And the corresponding prior:
prior_weibull = ComposedDistribution([
    Uniform(2000, 30000),
    Uniform(0.1, 5),
    Uniform(130000, min(data_modulus)),
])

# %%
# And for the Log Normal model:
results_lognormal = statistic_tool.execute(
    dataset=dataset, tested_distributions=["LogNormal"]
)

# %%
# And corresponding prior:
prior_lognormal = ComposedDistribution([
    Uniform(4, 15),
    Uniform(0.01, 5),
    Uniform(130000, min(data_modulus)),
])

# %%
# 2) Executing Bayesian inference
# ================================
# We can now sample the posterior distribution
# of the parameters of the normal model,
analysis_n.execute(
    likelihood_dist=Models.NORMAL,
    prior_dist=prior_normal,
    data=data_modulus,
    n_mcmc=N_MCMC,
)
analysis_n.save_results()
analysis_n.result

# %%
# of the parameters of the weibull model,
analysis_w.execute(
    likelihood_dist=Models.WEIBULL_MIN,
    prior_dist=prior_weibull,
    data=data_modulus,
    n_mcmc=N_MCMC,
)
analysis_w.save_results()
analysis_w.result

# %%
# of the parameters of the lognormal model,
analysis_l.execute(
    likelihood_dist=Models.LOG_NORMAL,
    prior_dist=prior_lognormal,
    data=data_modulus,
    n_mcmc=N_MCMC,
)
analysis_l.save_results()
analysis_l.result

# %%
# Then, we determine the burnin for each MCMC sampling.
# First for the Normal model:
analysis_n.plot_burnin(analysis_n.result, save=False, show=True)

# %%
# Then, the Weibull Min model:
analysis_w.plot_burnin(analysis_w.result, save=False, show=True)

# %%
# And the Log Normal model:
analysis_l.plot_burnin(analysis_l.result, save=False, show=True)

# %%
# A value of 50 for the burnin
# seems ok for sampler is thus selected.
burnin = 50

# %%
# Then, we post-process the results
# for each models before analyzing the results,
# first for the Normal model:
analysis_n.post(50, n_mcmc=N_MCMC, nb_samples_ml=10, nb_samples_posterior=5)
# then for the Weibull Min model:
analysis_w.post(50, n_mcmc=N_MCMC, nb_samples_ml=10, nb_samples_posterior=5)
# And the Log Normal model:
analysis_l.post(50, n_mcmc=N_MCMC, nb_samples_ml=10, nb_samples_posterior=5)

# %% Next,
# we generate the plots
# for the Normal model,
figs_n = analysis_n.plot_results()
# the Weibull Min model
figs_w = analysis_w.plot_results()
# and the Log Normal model
figs_l = analysis_l.plot_results()


# %%
# The first conclusion
# that can be drawn
# from the plots of the
# posterior samples
# for each model is that
# that priors were elicited.

# %%
# 3) Validating models
# ==================================
# We aim now to validate models.
# From the earlier posterior predictive plots,
# we can perform qualitative analyses.
# The posterior predictive distributions
# refer to predictions for all models
# averaged over all posterior samples.
# Though the predictions
# from all models are rather coherent
# with respect to the data,
# those from the Normal model are not
# as relevant as for the others.
# In particular,
# they are symmetric
# contrary to the data.
# It is harder to discriminate
# between the two other models
# using only visual plots.

# To continue the analyses,
# we study several numerical indicators,
# lppds and marginal likelihoods.
# We instanciate a class PosteriorChecks
# to analyze and summarize the results,
check_n = PosteriorChecks(analysis_n.result)
check_l = PosteriorChecks(analysis_l.result)
check_w = PosteriorChecks(analysis_w.result)

# %%
# Aside from posterior predictive plots
# that are qualitative assessments,
# we can focus on quantitative metrics
# that will account in particular
# for the fact that the Weibull and Lognormal models
# have higher number of parameters.

print(check_n)
print(check_w)
print(check_l)

# %%
# Consistently with earlier observations,
# the Weibull model seems to have
# the best predictive accuracy
# according to the lppd.
# The marginal likelihoods
# are harder to compare
# because the priors
# for the Weibull and Lognormal models
# have much wider support,
# penalizing thus heavily these models.
# It is interesting to notice
# that the ml for the Lognormal model
# in spite of a much wider support,
# has a better predictive accuracy
# sufficiently larger to compensate
# the difference from the priors.

# %%
# 4). The Weibull model
# and the Lognormal have 3 parameters
# instead of 2 for the Normal
# with the default parametrization
# of OpenTURNS distribution.
# We try to calibrate these two models
# by freezing some parameters,
# (the location parameter)
# which is carried out
# by indicating the frozen parameters
# and their associated values.
# ==================================
prior_weibull_b = ComposedDistribution([Uniform(50_000, 200_000), Uniform(1, 100)])
dict_frozen = {"frozen_index": [2], "frozen_values": [0]}

# %%
# We can now sample as earlier
# the posterior distribution
# of the parameters of the new models.
analysis_w_b = BayesTool(working_directory="weibullmin_2_frozen")
analysis_w_b.execute(
    likelihood_dist=Models.WEIBULL_MIN,
    prior_dist=prior_weibull_b,
    data=data_modulus,
    n_mcmc=N_MCMC,
    frozen_variables=dict_frozen,
)
analysis_w_b.save_results()

prior_lognormal_b = ComposedDistribution([Uniform(2, 20), Uniform(0.005, 0.5)])
analysis_l_b = BayesTool(working_directory="lognormal_2_frozen")
analysis_l_b.execute(
    likelihood_dist=Models.LOG_NORMAL,
    prior_dist=prior_lognormal_b,
    data=data_modulus,
    n_mcmc=N_MCMC,
    frozen_variables=dict_frozen,
)
analysis_l_b.save_results()

# %%
# Then,
# we determine the burnin for each MCMC sampling:
analysis_w_b.plot_burnin(analysis_w_b.result, save=True, show=True)
analysis_l_b.plot_burnin(analysis_l_b.result, save=True, show=True)

# Finally,
# as earlier,
# we launch several
# post-processing analyses:
analysis_w_b.post(50)
# And the Log Normal model:
analysis_l_b.post(50)


# %% and generate the plots
# the Weibull Min model
figs_w_b = analysis_w_b.plot_results()
# and the Log Normal model
figs_l_b = analysis_l_b.plot_results()

# %%
# First,
# for each model,
# the posterior samples
# are not uniformly distributed
# showing that priors were elicited.

# Furthermore,
# posterior predictive plots show
# that with a smaller number
# of degrees of freedom,
# the Weibull seems less appropriate
# than the Lognormal model.


# Finally, we instanciate
# the new checks:
check_l_b = PosteriorChecks(analysis_l_b.result)
check_w_b = PosteriorChecks(analysis_w_b.result)

# We can compute next the different criteria
# for the different models.
print(check_n)
print(check_w_b)
print(check_l_b)

# %%
# By removing a degree of freedom
# the Weibull model becomes less accurate,
# The downgrade for the Lognormal model
# is not as significant.
# These conclusions are consistent
# with the observations
# from the posterior predictive plots.
# The marginal likelihoods
# are harder to compare
# because the priors
# are not compatible,
# either wider (Lognormal model)
# or smaller (Weibull model).
