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
#        :author: Jorge CAMACHO-CASERO
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
Usage of the SensitivityTool
============================

SensitivityTool provides methods for sensitivity analysis.
BendingTestAnalytical is used to illustrate the use of this tool.
"""

# %%
# Import the packages
# --------------------------
from __future__ import annotations

import logging

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.sensitivity.sensitivity import SensitivityTool
from vimseo.tools.space.space_tool import SpaceTool

activate_logger(level=logging.INFO)

# %%
# Analysis definition
# --------------------------
# Let's start instantiate a model:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/sensitivity",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/sensitivity",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/sensitivity/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# Create a parameter space
# --------------------------
# Based on the above, we create a parameter space. In this example, all the
# parameters are defined by Uniform distributions. The parameter spaces are built
# with the help of the SpaceTool. By default, a parameter space
# per load case is generated (if load_cases=None):

space_tool = SpaceTool(working_directory="SpaceTool_results")
print(space_tool.get_available_space_builders())

# %%
# First, consider all input variables of the model except "relative_dplt_location".

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
print(space_tool.parameter_space)

# %%
# Using the SensitivityTool
# --------------------------
# First, the tool must be instantiated.

tool = SensitivityTool(working_directory="sensitivity_tool_results")

# %%
# The :class:`~.SensitivityTool` must be executed to generate the Design of Experiments.
# By default, it creates the sensitivity analysis through the |gemseo| API,
# computes sensitivity analysis indices and,
# generates a radar plot with the results.
# The execution returns either a dictionary or a pandas dataframe
# (if argument as_df=True).

output_names = ["reaction_forces", "dplt_at_force_location", "maximum_dplt"]
sensitivity_indices = tool.execute(
    model=model,
    parameter_space=space_tool.parameter_space,
    sensitivity_algo="MorrisAnalysis",
    output_names=output_names,
    n_replicates=5,
).indices
tool.save_results()

print(tool.result)

# %%
# The ``MorrisAnalysis`` method is used by default for the sensitivity analysis,
# but there is also the option to use 'CorrelationAnalysis' or 'SobolAnalysis'

# %%
# Plot the sensitivity of ``reaction_forces`` to the model inputs.
# Standard plots for each type of sensitivity analysis can be shown.
# Here, for a Morris analysis, a radar plot of the indices,
# and a ($\sigma$, $\mu_{star}$) plot:
fig_sensitivity_reaction_forces = tool.plot_results(
    tool.result,
    output_names=output_names,
    show=True,
    save=False,
)

# And an interactive bar plot of the indices:
fig_sensitivity_reaction_forces["bar_plot"]
