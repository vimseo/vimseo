# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Jorge CAMACHO-CASERO
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
#        :author: benedicte REINE
"""
Usage of the BendingTestAnalytical
==================================

BendingTestAnalytical is a simple model implemented for testing and training purpose.
"""

from __future__ import annotations

import logging

from gemseo.core.discipline import Discipline
from numpy import array

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings

activate_logger(level=logging.INFO)

# %%
# Introduction
#
# BendingTestAnalytical is based on Bernoulli beam theory. It is configured on imposed
# displacement. It computes the reaction forces and the displacement and moment along
# the beam.
#
# First, let's instantiate the model from the API:

model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/basic_usage",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/basic_usage",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/basic_usage/{model_name}_{load_case}_cache.hdf",
    ),
)
model.set_cache(Discipline.CacheType.NONE)
model.archive_manager._accept_overwrite_job_dir = True

# %%
# The model description can be accessed like this:
# Note that the load case contains the names of the boundary conditions,
# and the output variables to be plotted on x-y plots:
print(model.description)

# %%
# An illustration of the model can be shown:
model.show_image()
# and the path to the image accessed like this:
model.image_path

# %%
# Specific image can also be associated with the load case:
model.load_case.show_image()

# %%
# Executing the model with default parameters is straightforward:

model.execute()

# %%
# And input parameters could also be redefined.
# First get the list of parameters:

model.get_input_data_names()

# %%
# Then modify inputs, for instance, Young's modulus:

model.execute({"young_modulus": array([195000.0])})

# %%
# Switching load cases:
# A new model must be created to switch to another load case:

model = create_model("BendingTestAnalytical", "ThreePoints")

# It is also possible to specify values for other inputs:
output_data = model.execute({"height": array([20.0])})
print(output_data)

# %%
# ## Post-treatment of the results
#
# The BendingTestAnalytical provides the following outputs:
#
# - reaction_forces: a scalar value giving the reaction forces calculated at the
# - maximum_dplt: a scalar value giving the maximum displacement of the beam
# - location_max_dplt: a scalar value giving the location of the maximum displacement along the beam
# - displacement: an array of displacement values
# - displacement_grid: an array of sorted coordinates along the beam at which displacement are computed
# - moment: an array of moment values
# - moment_grid: an array of sorted coordinates along the beam at which

# The value of the maximum displacement along the beam can be obtained like this:

model.get_output_data()["maximum_dplt"]


# %%
# And the outputs plotted like this:

figures = model.plot_results(save=True, show=True)

figures["dplt_vs_dplt_grid"]

# %%
# And now, we want to change the support location.
# By default, it is located at both ends of the beam.
# It is now positioned at 0.3 times the half length of the beam.

output_data = model.execute({"relative_support_location": array([0.3])})

# %%
# Note that the reaction force has increased compared to the previous simulation,
# because the support are closer to the beam center.
print(output_data)

# %%
# The outputs can be plotted again. Note that the displcement curve support
# now corresponds to +/- 0.3 times the half length of the beam:

figures = model.plot_results(show=True)

figures["dplt_vs_dplt_grid"]

# %%
# For a model running an external solver, the options of the job
# can be modified.
# The basic job options are defined in the pydantic model ``BaseUserJobSettings()``
# and passed to the model's job executor. To set the number of CPUs to 2,
# the following command can be used:
# ``model.run.job_executor.set_options(BaseUserJobSettings(n_cpus=2))``.
