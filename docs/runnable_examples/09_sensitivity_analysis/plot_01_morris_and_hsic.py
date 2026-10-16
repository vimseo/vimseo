# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
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
Global sensitivity analysis: Morris and HSIC
============================================

The :class:`~.SensitivityTool` ranks the inputs of a model
by their influence on its outputs over a whole parameter space,
with the Morris or the HSIC method.
It either samples the model itself
or uses the samples of a DOE prepared in advance.
``BendingTestAnalytical`` is used to illustrate the use of this tool.

For a local analysis around nominal values, see the One-factor-at-a-Time example.
"""

# %%
# Import the packages
# --------------------------
# %%
from __future__ import annotations

import logging

import mlflow
from gemseo.core.discipline import Discipline
from mlflow import delete_run

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.doe.doe import DOEInputs
from vimseo.tools.doe.doe import DOESettings
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.sensitivity.sensitivity import SensitivityTool
from vimseo.tools.sensitivity.sensitivity import SensitivityToolInputs
from vimseo.tools.sensitivity.sensitivity import SensitivityToolSettings
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
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/sensitivity",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/sensitivity",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/sensitivity/{model_name}_{load_case}_cache.hdf",
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
# -------------------------
# The tool samples the model over the parameter space
# and computes the sensitivity indices through the GEMSEO API.
# The settings of the analysis are:
#
# - ``sensitivity_algo``: the sensitivity method,
#   either ``"MorrisAnalysis"`` (default) or ``"HSICAnalysis"``,
# - ``n_replicates``: for the Morris method, the number of One-factor-at-a-Time
#   trajectories, each one starting from a random point;
#   along a trajectory, each input varies in turn,
#   the previous ones keeping their new values,
# - ``n_samples``: the number of samples; if 0, it is deduced from the method,
#   e.g. ``n_replicates`` times the number of inputs plus one for Morris.
output_names = ["reaction_forces", "dplt_at_force_location", "maximum_dplt"]
tool = SensitivityTool(working_directory="sensitivity_tool_results")
tool.execute(
    inputs=SensitivityToolInputs(
        model=model, parameter_space=space_tool.parameter_space
    ),
    settings=SensitivityToolSettings(
        output_names=output_names, sensitivity_algo="MorrisAnalysis", n_replicates=5
    ),
)
tool.save_results()
print(tool.result)

# %%
# The Morris indices are, for each output and input component,
# statistics of the elementary effects of the input over the trajectories:
#
# - ``mu``: their mean,
# - ``mu_star``: the mean of their absolute values,
#   which measures the influence of the input,
# - ``sigma``: their standard deviation,
#   which reveals non-linear effects and interactions,
# - ``relative_sigma``: ``sigma`` divided by ``mu_star``,
# - ``min`` and ``max``: the extrema of their absolute values.
#
# They can be tabulated; by default, the main indices ``mu_star`` are used:
tool.result.get_indices_dataframe()

# %%
# Standard plots of a Morris analysis can be shown:
# a radar plot of the indices, a bar plot and a ($\sigma$, $\mu^*$) plot
# for each output.
# Here, the interactive bar plot:
figures = tool.plot_results(
    tool.result, output_names=output_names, show=False, save=False
)
figures["bar_plot"]

# %%
# Using the samples of a DOE prepared in advance
# ----------------------------------------------
# The samples can be computed beforehand by a :class:`~.DOETool`,
# for instance on a cluster,
# and then its result is passed to the :class:`~.SensitivityTool` as ``doe_result``:
# the model is not executed again.
# This result records the DOE algorithm, which the tool checks.
#
# For a Morris analysis, the DOE must be generated by the DOE algorithm
# ``"MorrisDOE"``,
# whose ``n_samples`` is the number of replicates times the number of inputs plus one.
# Its settings are passed through ``algo_settings``,
# here the relative step of the trajectories in the unit hypercube.
n_replicates = 5
doe_tool = DOETool(working_directory="morris_doe_results")
doe_tool.execute(
    inputs=DOEInputs(model=model, parameter_space=space_tool.parameter_space),
    settings=DOESettings(
        output_names=output_names,
        algo="MorrisDOE",
        n_samples=n_replicates * (space_tool.parameter_space.dimension + 1),
        algo_settings={"step": 0.05},
    ),
)
doe_tool.result.dataset

# %%
# The Morris indices divide the output variations by the step of the DOE.
# This step is read from the settings recorded in the DOE result,
# so it does not have to be passed again and cannot differ from the samples.
tool = SensitivityTool(working_directory="morris_from_doe_results")
tool.execute(
    inputs=SensitivityToolInputs(doe_result=doe_tool.result),
    settings=SensitivityToolSettings(
        output_names=output_names, sensitivity_algo="MorrisAnalysis"
    ),
)
tool.result.get_indices_dataframe("sigma")

# %%
# A HSIC analysis requires samples that are independent and identically
# distributed (i.i.d.) according to the probability distribution of the parameter
# space, i.e. a Monte Carlo sampling.
# A Latin Hypercube Sampling or a quasi Monte Carlo sequence is not suitable:
# its samples are not independent, which biases the HSIC estimators.
# So the DOE algorithm must be ``"OT_MONTE_CARLO"``, ``"OT_RANDOM"`` or ``"MC"``.
doe_tool = DOETool(working_directory="monte_carlo_doe_results")
doe_tool.execute(
    inputs=DOEInputs(model=model, parameter_space=space_tool.parameter_space),
    settings=DOESettings(
        output_names=output_names, algo="OT_MONTE_CARLO", n_samples=30
    ),
)

# %%
# The main HSIC indices are the ``r2_hsic`` ones,
# i.e. the HSIC indices normalized between 0 and 1.
tool = SensitivityTool(working_directory="hsic_from_doe_results")
tool.execute(
    inputs=SensitivityToolInputs(doe_result=doe_tool.result),
    settings=SensitivityToolSettings(
        output_names=output_names, sensitivity_algo="HSICAnalysis"
    ),
)
tool.result.get_indices_dataframe()

# %%
# Using runs searched in an MLflow archive
# ----------------------------------------
# The samples of a HSIC analysis do not have to come from a DOE:
# any dataset of runs can be passed as ``dataset``,
# e.g. runs gathered over several studies and searched in an archive.
# Here, the runs are archived in [MLflow](https://mlflow.org).
# The model archives its runs in the experiment ``"hsic_samples"``.
# Its cache only keeps the last evaluation in memory,
# so that every point of the DOE is run and archived once,
# even when the example is executed again.
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "mlflow_archive/sensitivity",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/sensitivity",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/sensitivity/{model_name}_{load_case}_mlflow_cache.hdf",
        archive_manager="MlflowArchive",
    ),
)
model.set_cache(Discipline.CacheType.SIMPLE)
experiment_name = "hsic_samples"
model.archive_manager.set_experiment(experiment_name)

# %%
# The runs of a previous execution of this example are deleted:
for run_id in mlflow.search_runs(experiment_names=[experiment_name])["run_id"]:
    delete_run(run_id)

# %%
# The archive is populated by a Monte Carlo sampling;
# in practice, the runs would come from previous studies.
DOETool(working_directory="mlflow_doe_results").execute(
    inputs=DOEInputs(model=model, parameter_space=space_tool.parameter_space),
    settings=DOESettings(
        output_names=output_names, algo="OT_MONTE_CARLO", n_samples=30
    ),
)

# %%
# The successful runs, whose error code is zero, are searched in the archive
# (see the [MLflow search syntax](https://mlflow.org/docs/latest/ml/search/search-runs/));
# the metadata of the runs, like the error code, are stored as tags.
# The query could also filter on the inputs,
# but it would then restrict their distribution,
# so the samples would no longer follow the one of the parameter space.
runs = mlflow.search_runs(
    experiment_names=[experiment_name], filter_string="tags.error_code = '0'"
)
runs

# %%
# A cache is built from these runs,
# and converted into a dataset restricted to the inputs of the parameter space
# and to the analyzed outputs:
cache = model.create_cache_from_archive(run_ids=runs["run_id"])
dataset = cache.to_dataset(
    input_names=space_tool.parameter_space.variable_names, output_names=output_names
)
dataset

# %%
# The dataset is passed to the HSIC analysis.
# Its samples must still be i.i.d. according to the probability distribution
# of the inputs, which the tool cannot check, hence a warning.
# The tool wraps the dataset into a DOE result
# whose DOE algorithm is ``"Unstructured"``;
# like a DOE executed by the tool or prepared in advance,
# this DOE result is saved in the subdirectory ``DOETool`` of the tool.
tool = SensitivityTool(working_directory="hsic_from_mlflow_results")
tool.execute(
    inputs=SensitivityToolInputs(dataset=dataset),
    settings=SensitivityToolSettings(
        output_names=output_names, sensitivity_algo="HSICAnalysis"
    ),
)
tool.save_results()
tool.result.get_indices_dataframe()
