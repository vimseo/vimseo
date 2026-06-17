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

# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Ludovic BARRIERE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
Usage of the SurrogateTool for semi-analytical beam Model
=========================================================

:class:`~.SurrogateTool` provides methods for the generation of surrogate models.
It identifies the best surrogate and associated quality measures within a list of
default surrogate candidates.
It uses either a default list of candidates or candidates specified by the user.
The :class:`~.BendingTestAnalytical` is used to illustrate the use of this tool.
"""

# %%
# Import the packages
# --------------------------
# %%
from __future__ import annotations

import logging
import pprint

from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from numpy import array

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.tools.surrogate.surrogate import SurrogateTool

activate_logger(level=logging.INFO)

# %%
# Model and parameter space
# --------------------------
# Load the model (here a simple analytical beam model):

model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/surrogate",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/surrogate",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/surrogate/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# The SpaceTool provides methods to build parameter spaces.
# One can check available builders first:

space_tool = SpaceTool(working_directory="SpaceTool_results")

# %%
# Build a parameter space based on custom minimum and maximum values.
# This parameter space has 2 scalar variables with large variations.
space_tool.execute(
    distribution_name="OTTriangularDistribution",
    space_builder_name="FromMinAndMax",
    minimum_values={
        # "length": 200.0,
        # "width": 5.0,
        "height": 5.0,
        "imposed_dplt": 0.0,
        # "relative_dplt_location": 0.5,
    },
    maximum_values={
        # "length": 1000.0,
        # "width": 50.0,
        "height": 50.0,
        "imposed_dplt": 20.0,
        # "relative_dplt_location": 1.0,
    },
)
print(space_tool.parameter_space)

# %%
# Create a :class:`~.gemseo.datasets.dataset.Dataset` (from a DOE)
# ----------------------------------------------------------------
# The :class:`~.SurrogateTool` used a dataset from which the surrogate model is generated.
# In this example we build the dataset by
# creating a DOE. However, the dataset could be manually created,
# or imported from a HDF5 cache file.
# To generate a dataset from a DOE we use the :class:`~.DOETool`, along with the :class:`~.SpaceTool`.

doe_tool = DOETool(working_directory="doe_tool_results")
dataset = doe_tool.execute(
    model=model,
    parameter_space=space_tool.parameter_space,
    output_names=["reaction_forces"],
    algo="OT_OPT_LHS",
    n_samples=200,
).dataset
print(dataset)

# %%
# The generated dataset can also be plotted in a scatter matrix

scatter_matrix = ScatterMatrix(dataset)
scatter_matrix.execute(save=False, show=True)
fig = scatter_matrix.figures[0]

fig

# %%
# Building a surrogate model
# --------------------------

surrogate_tool = SurrogateTool(working_directory="surrogate_tool_results")

# %%
# Settings of the tool can be checked (other options can be redefined throughout
# :code:`surrogate_tool.update_options()`):

pprint.pprint(surrogate_tool.options)

# %%
# There are two main ways for using the SurrogateTool:
#
# * One wants to use a specific surrogate function (e.g. 2nd order polynomial regression)
#
# .. code::
#
#    surrogates = surrogate_tool.execute(model=model, doe_results=dataset,
#                                        algo="PolynomialRegressor", algo_options={"degree": 2, "fit_intercept": True}
#                                        output_names=["dplt_at_force_location"])

# %%
#
# * One wants to select the best surrogate function over a set of candidates and their
# parameters (default candidates and other options can be redefined throughout
# :code:`surrogate_tool.update_options()`). A quality measure (associated with an
# evaluation method) is used. By default, it uses "Mean Squared Error" with
# "kfolds" evaluation method.

surrogate_results = surrogate_tool.execute(
    model=model,
    dataset=dataset,
    output_names=["reaction_forces"],
    quality_measures=["MSEMeasure", "R2Measure"],
)
surrogate_tool.save_results()
surrogate = surrogate_results.model
print(surrogate_tool.selected_algo)

# %%
# .. note::
#    It is possible to redefine candidate algorithms and their options (see |gemseo|
#    documentation for available algorithms).
#
#    .. code::
#
#        custom_candidates = {"RBFRegressor": {},
#                             "LinearRegressor", {'fit_intercept': [True, False]},
#                             "PolynomialRegressor", {'degree': [4, 5], 'fit_intercept': [True, False]}
#                             }
#        surrogate_tool.set_candidates(custom_candidates)
#

# %%
# The surrogate model can then be used in place of the model (outputs restricted to "dplt_at_force_location"):

input_data = {
    # "young_modulus": array([150000.0]),
    # "length": array([5450.0]),
    # "width": array([245.0]),
    "height": array([35.0]),
    "imposed_dplt": array([10.0]),
}
output = surrogate.execute(input_data)
output["reaction_forces"]

# %%
# which can be compared to prediction of the original model:

true_output = model.execute(input_data)
true_output["reaction_forces"]

# %%
# Analysing the quality of surrogates
# -----------------------------------
# SurrogateTool comes with functions to analyse several quality measures that could be complementary.
# One can define the quality measures to be evaluated, as well as the evaluation methods
# (alternatively, use default selection). Here, default ones are considered.
#
# Qualities are computed at each call to :meth:`~.execute()` method, but can be computed
# again with other parameters by :meth:`~.compute_quality()` method.
#
# Then, show the quality measures:

print(surrogate_tool.result)

# %%
# Predictions versus observations can be plotted:

figures = surrogate_tool.plot_results(
    surrogate_tool.result,
    output_names=["reaction_forces"],
    show=True,
    save=False,
)

# %%
# The user is invited to visit the |gemseo| documentation for a complete view of the
# available functionalities for surrogate generation and exploitation.
