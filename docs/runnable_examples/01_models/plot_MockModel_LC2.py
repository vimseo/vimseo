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
Overview of the MockModel for load case LC2
========================================================================================

 A toy model implementing an unphysical analytical law; used for testing purpose
"""

# %%
from __future__ import annotations

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings

# %%
# First, let's instantiate the model for a given load case:

model_name = "MockModel"
load_case = "LC2"
model = create_model(
    model_name,
    load_case,
    check_subprocess=True,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/model_gallery",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/model_gallery",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/model_gallery/{model_name}_{load_case}_cache.hdf",
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


# %%
# Plot of y1_2_vs_y1

figures["y1_2_vs_y1"]
