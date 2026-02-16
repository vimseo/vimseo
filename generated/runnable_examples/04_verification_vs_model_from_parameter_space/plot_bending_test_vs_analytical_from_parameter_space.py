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
Usage of the model-to-model solution verification tool on a Finite-Element (Abaqus) model
=========================================================================================

Check an Abaqus cantilever beam model versus an analytical model with the
'CodeVerificationAgainstModelFromParameterSpace' tool using as input a parameter
space."""

from __future__ import annotations

import logging

from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.tools.verification.verification_vs_model_from_parameter_space import (
    CodeVerificationAgainstModelFromParameterSpace,
)

# %%
# We first define the logger level:
activate_logger(level=logging.INFO)

# %%
# In this example, the two models are compared over an input parameter space.
# So we need to generate a space of parameters.
# It is obtained using the ``SpaceTool`` and choosing the ``FromModelCenterAndCov``
# builder.
space_tool = SpaceTool(working_directory="SpaceTool_results")
space_tool.execute(
    distribution_name="OTTriangularDistribution",
    space_builder_name="FromMinAndMax",
    minimum_values={
        "length": 200.0,
        "height": 5.0,
        "imposed_dplt": 0.0,
        "relative_dplt_location": 0.1,
    },
    maximum_values={
        "length": 1000.0,
        "height": 50.0,
        "imposed_dplt": 20.0,
        "relative_dplt_location": 1.0,
    },
)
print(space_tool.parameter_space)


# %%
# Then let's create the model to verify:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/verification_vs_model",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/verification_vs_model",
    ),
)
model.cache = None

# %%
# And the reference model:
model_2 = create_model(
    "BendingTestAnalytical",
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/verification_vs_model_2nd_model",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/verification_vs_model_2nd_model",
    ),
)
model_2.cache = None

# %%
# All inputs to the verification are now available.
# We create the verification tool we are interested in.
verificator = CodeVerificationAgainstModelFromParameterSpace(
    directory_naming_method=DirectoryNamingMethod.NUMBERED,
    working_directory="CodeVerificationAgainstModelFromParameterSpace_results",
)

# %%
# The options can be modified.
# Alternatively, options can be passed as keyword arguments to
# ``CodeVerificationAgainstModelFromParameterSpace()`` constructor.
verificator.options["metric_names"] = [
    "SquaredErrorMetric",
    "RelativeErrorMetric",
    "AbsoluteErrorMetric",
]

# %%
# The verification is now executed on 50 samples using by default an optimised Latin
# hypercube algorithm.
# Note that the verification is here restrained to the output variable
# ``reaction_forces``, and that a description of the verification can be provided.
verificator.execute(
    model=model,
    reference_model=model_2,
    parameter_space=space_tool.result.parameter_space,
    n_samples=5,
    output_names=["reaction_forces", "maximum_dplt", "location_max_dplt"],
)

# %%
# The result contains the error metrics:
verificator.result.integrated_metrics

# %%
# And saved on disk.
verificator.save_results()

# %%
# The saved results can be loaded in a dedicated dashboard to be explored.
# The dashboard is opened by typing ``dashboard_verification`` in a terminal,
# and selecting the tab ``Comparison case``.

# %%
# The results can also be plotted from the Python API.
# It shows the scatter matrix of the inputs:
figures = verificator.plot_results(
    verificator.result,
    "RelativeErrorMetric",
    "reaction_forces",
    save=False,
    show=True,
    directory_path=verificator.working_directory,
)

# %%
# and an histogram of the errors:
figures["error_metric_histogram"]
