# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
1) Usage of the Uncertainty Quantification
==========================================

The :class:`~.StatisticsTool` provides methods for quantifying uncertainties
on a model output.
The :class:`~.BendingTestAnalytical` is used to illustrate the use of this tool.
"""

from __future__ import annotations

import logging
from pprint import pprint

from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.scatter import Scatter
from matplotlib import pyplot as plt
from numpy import array

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.tools.statistics.statistics_tool import StatisticsTool

activate_logger(level=logging.INFO)

model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/uq",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/uq",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/uq/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# It is possible to change a default input of the model.
model.default_input_data.update({"imposed_dplt": array([-15.0])})

# %%
# 2. Define the uncertain space
# =============================
#
# In addition to the model,
# we need to define the uncertain space over which statistics will be computed.
# The uncertainty is filled with independent random variables.
# This operation is performed with the :class:`~.SpaceTool`.
# Several builders can be used to construct the distributions.
space_tool = SpaceTool(working_directory="SpaceTool_results")
print(space_tool.get_available_space_builders())

# %%
# The model can be used as input such that the bounds of the model input variables
# or the central value of its input variable intervals can be used to build
# the probability distributions of the random variables.
# Here the uncertain space is built from the model, using the central value of its
# input variable intervals. A coefficient of variation is used to define the width
# of the distribution, which is :math:`\pm cov * central\_value`.
# We consider independent random variables triangularly distributed:
#
# .. note::
#
#    A triangular distribution is a probability distribution
#    defined by a lower bound, a mode and an upper bound:
#
#    .. figure:: /_examples/uq/_static/triangular_distribution.png
#
#       Probability density function of the random variable *friction*
#       distributed as a triangular distribution :math:`\mathcal{T}(0.1, 0.2, 0.3)`.
#
# Here, the space of parameters is built in two steps.
# First, considering all input variables of the model except "relative_dplt_location".

retained_variables = model.get_input_data_names()
retained_variables.remove("relative_dplt_location")
space_tool.execute(
    distribution_name="OTTriangularDistribution",
    space_builder_name="FromModelCenterAndCov",
    variable_names=retained_variables,
    use_default_values_as_center=True,
    model=model,
    cov=0.05,
)

# %%
# Then, specifically for "relative_dplt_location".

space_tool.execute(
    distribution_name="OTTriangularDistribution",
    space_builder_name="FromCenterAndCov",
    center_values={"relative_dplt_location": 0.9},
    cov=0.05,
)
parameter_space = space_tool.parameter_space

# %%
# Other distributions can be used and the available ones can be listed with:
print(space_tool.get_available_distributions())

# %%
# .. note::
#
#    For a one-shot use,
#    we can also instantiate a uncertain space
#    directly from :class:`ParameterSpace`.
#
#    .. code::
#
#       from gemseo.api import create_parameter_space
#
#       parameter_space = create_parameter_space()
#       for (name, minimum, mode, maximum) in [
#           ("plate_len", 210, 214.3, 220.0),
#             ("plate_wid", 50.5, 50.8, 51.0),
#             ("plate_thick", 2.9, 3.0, 3.1),
#             ("friction", 0.1, 0.2, 0.3),
#             ("boundary", 57000.0, 60000.0, 63000.0),
#             ("huth_factor", 0.95, 1., 1.05),
#             ("preload", -10500., -10000., -9500.)
#       ]:
#           parameter_space.add_random_variable(
#               name,
#               "OTTriangularDistribution",
#               minimum=minimum,
#               maximum=maximum,
#               mode=mode
#           )
#
#    In this case, we can use any distribution of
#    `OpenTURNS <https://openturns.github.io/openturns/latest/user_manual/
#    probabilistic_modelling.html>`__
#    and
#    `SciPy <https://docs.scipy.org/doc/scipy/reference/
#    stats.html#probability-distributions>`__.

# %%
# Discover this uncertain space and check its content by printing it:
print(parameter_space)

# %%
# We can also sample this uncertain space:
three_samples = parameter_space.compute_samples(3, as_dict=True)
print("Three samples in the parameter space", three_samples)

# %%
# 3. Post-process
# ===============
# Lastly, we can generate some visualizations from 200 realizations of the input
# variables:
dataset = Dataset.from_array(
    parameter_space.compute_samples(200), parameter_space.uncertain_variables
)

# %%
# |gemseo| provides several plots in package :package:`gemseo.post.dataset`.
# Here, these 200 realizations for a pair of variables are shown in a scatter plot:
scatter_plot = Scatter(
    dataset,
    x="length",
    y="width",
)
fig = scatter_plot.execute(
    show=True,
    save=False,
    directory_path=space_tool.working_directory,
    file_format="html",
)
fig

# %%
# Dedicated plots from |v| tools can also be used.
# For instance, the :class:`~.SpaceTool` provides a scatter matrix plot
# where the diagonal blocks represent the histograms of the random variables
# while the other blocks represents the value of a variable versus another.
space_tool.plot_results(space_tool.result, save=False, show=True, n_samples=200)
# Workaround for HTML rendering, instead of ``show=True``
plt.show()

# %%
# .. seealso::
#
#    `Examples of visualization tools <https://gemseo.readthedocs.io/en/stable/examples/dataset/index.html>`__
#    to post-process a :class:`~.gemseo.datasets.dataset.Dataset`.
#

# %%
# 3. Sample the model
# ===================
# Then,
# we generate 100 input-output samples of the model
# by sampling the discipline with the :class:`~.DOETool` executed from a design of
# experiments (DOE). The :class:`~.DOETool` is based on :class:`~.gemseo.core.doe_scenario.DOEScenario`
# To place the samples over the input space, we can use an optimal
# `latin hypercube sampling (LHS) <https://en.wikipedia.org/wiki/Latin_hypercube_sampling>`__ technique.
#
# .. note::
#
#    The LHS technique implemented by ``"OT_LHS"`` or ``"lhs"`` is stochastic:
#    given a number of samples :math:`N` and an input space of dimension :math:`d`,
#    executing it twice will lead to two different series of samples.
#    Here, we are looking for the series of samples that best covers the input space
#    (we talk about space-filling DOE);
#    for that,
#    we use ``"OT_OPT_LHS"`` relying on a global optimization algorithm
#    (simulated annealing).
#
doe_tool = DOETool(working_directory="doe_tool_results")
output_names = ["reaction_forces"]
dataset = doe_tool.execute(
    model=model,
    parameter_space=parameter_space,
    output_names=output_names,
    algo="OT_OPT_LHS",
    n_samples=100,
).dataset

# %%
# The Dataset containing the DOE result is a
# `Pandas <https://pandas.pydata.org>`__
# ``DataFrame``.
# People used to Pandas can go much further in terms of data analysis
# (filtering, plotting, sorting, ...).
print(dataset.describe())
dataset.to_csv(doe_tool.working_directory / "data.csv", sep=";")

# %%
# 4. Compute statistics
# =====================
# The :class:`~.StatisticsTool` relies on |gemseo| to compute statistics
# on a sampling. It allows to test several probability distributions
# to find the one that best fits to the output distribution according
# to a fitting criterion and a selection criterion.
# Then, based on this synthetic distribution, several statistics indicators
# can be computed like mean value, standard deviation or percentiles.

# %%
# Select the output variable on which statistics are computed.
output_name = output_names[0]

# %%
# The following options are used by default:
pprint(StatisticsTool().options)

# %%
# Default options can be overriden through the :meth:`~.StatisticsTool.execute` method.
# Here the confidence value is modified.
statistic_tool = StatisticsTool(working_directory="statistics_tool_results")
results = statistic_tool.execute(
    dataset=dataset,
    variable_names=[output_name],
    confidence=0.98,
)
print(results)

# %%
# The fitted synthetic distribution can be plotted.
statistic_tool.plot_results(results, variable=output_name, save=False, show=True)
