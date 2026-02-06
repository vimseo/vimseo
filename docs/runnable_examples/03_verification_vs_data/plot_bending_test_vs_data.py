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
Usage of the model-versus-data code verification tool on a Finite-Element (Abaqus) model
=========================================================================================

Check an Abaqus cantilever beam model versus a reference dataset with the
'CodeVerificationAgainstData' tool.
"""

from __future__ import annotations

import logging

from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.verification.verification_vs_data import CodeVerificationAgainstData

# %%
# We first define the logger level:
activate_logger(level=logging.INFO)

# %%
# Then we create the model to verify:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/verification_vs_data",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/verification_vs_data",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/verification_vs_data/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# We also need a reference dataset.
# Here we do it programmatically, but we can also create it from a csv file:
# ``
reference_data = IODataset().from_array(
    data=[[10.0, 10.0, -4.0, -12.0], [15.0, 10.0, -6.0, -40.0]],
    variable_names=["height", "width", "maximum_dplt", "reaction_forces"],
    variable_names_to_group_names={
        "height": "inputs",
        "width": "inputs",
        "maximum_dplt": "outputs",
        "reaction_forces": "outputs",
    },
)

# %%
# All inputs to the verification are now available.
# We create the verification tool we are interested in.
verificator = CodeVerificationAgainstData(
    directory_naming_method=DirectoryNamingMethod.NUMBERED,
    working_directory="CodeVerificationAgainstData_results",
)

# The options can be modified.
# Alternatively, options can be passed as keyword arguments to
# ``CodeVerificationAgainstModelFromParameterSpace()`` constructor.
verificator.options["metric_names"] = [
    "SquaredErrorMetric",
    "RelativeErrorMetric",
    "AbsoluteErrorMetric",
]

verificator.execute(
    model=model,
    reference_data=reference_data,
    output_names=["maximum_dplt", "reaction_forces"],
    description={
        "title": "Verification of a cantilever analytic beam for a variation of beam height.",
        "element_wise": ["Small height value", "High height value"],
    },
)

# %%
# The result contains the error metrics:
verificator.result.integrated_metrics

# %%
# And saved on disk, together with its metadata:
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
