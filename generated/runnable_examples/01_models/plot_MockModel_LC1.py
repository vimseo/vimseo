# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
# copyright section to be added automatically by syntax check
"""
Overview of the MockModel for load case LC1
========================================================================================

 A toy model implementing an unphysical analytical law; used for testing purpose
"""

from __future__ import annotations

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings

# %%
# First, let's instantiate the model for a given load case:

model_name = "MockModel"
load_case = "LC1"
model = create_model(
    model_name,
    load_case,
    check_subprocess=True,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/model_gallery",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/model_gallery",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/model_gallery/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# The model description can be accessed like this:

print(model.description)

# %%
# An illustration of the load case:

model.show_image()

# %%
# The model is executed with its default input values:

model.execute()

# %%
# And the results are visualised with the pre-defined plots:

figures = model.plot_results(show=True)
