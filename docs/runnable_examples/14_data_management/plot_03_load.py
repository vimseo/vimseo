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

"""
Load the results
================

Load a model result and an analysis node result from their reference, and go from an analysis node result
to its model results.
"""

# %%
from __future__ import annotations

import shutil

from gemseo.algos.parameter_space import ParameterSpace

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.api import create_model
from vimseo.api import load_analysis_node_results
from vimseo.api import load_model_results
from vimseo.api import search_analysis_node_runs
from vimseo.api import search_model_results
from vimseo.core.model_result import ModelResult

# %%
# Some results to load:
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR / "archive/data_management/load",
    "study_name": "load",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model(
    "BendingTestAnalytical",
    "Cantilever",
    **archive,
    cache_file_path=archive["directory_archive_root"] / "cache.hdf",
)
parameter_space = ParameterSpace()
parameter_space.add_random_variable(
    "height", "OTUniformDistribution", minimum=30.0, maximum=60.0
)
doe = DOEAnalysisNode(**archive)
doe.execute(model=model, parameter_space=parameter_space, n_samples=5)
analysis_node_run_id = doe.result.metadata.analysis_node_run_id

# %%
# Load from a reference
# ---------------------
# The summaries returned by the searches carry the ``uri`` of their result. A model
# result and an analysis node result are loaded from it the same way. A loading function takes
# one reference or many, and always returns a collection: ``[0]`` gives one result.
archived_model_runs = search_model_results(**archive)
archived_analysis_node_runs = search_analysis_node_runs(**archive)
model_result = load_model_results(archived_model_runs[0]["uri"], **archive)[0]
analysis_node_result = load_analysis_node_results(
    archived_analysis_node_runs[0]["uri"], **archive
)[0]

# %%
# A model result is referenced by its ``run_id``, ``run:{run_id}``, the path of its job
# directory or ``runs:/{mlflow_run_id}``; an analysis node result by its ``analysis_node_run_id``,
# ``analysis-node-run:{analysis_node_run_id}``, the path of its analysis node run directory or of its result
# file, or ``runs:/{mlflow_run_id}``. A reference of the other kind raises an error
# naming the right function:
run_id = archived_model_runs[0]["run_id"]
model_result = load_model_results(run_id, **archive)[0]
model_result.run_id

# %%
analysis_node_result = load_analysis_node_results(analysis_node_run_id, **archive)[0]
analysis_node_result.metadata.analysis_node_run_id

# %%
# Load many model results
# -----------------------
# An analysis node result knows the ``run_id`` of the simulations it used, from which the
# model results are loaded at once, in their order:
model_results = load_model_results(
    analysis_node_result.metadata.simulation_run_ids, **archive
)
model_result = model_results[0]
model_result.scalars(["height", "reaction_forces"])

# %%
# The scalars of a result are told apart by group:
sorted(model_result.scalars(group="inputs"))

# %%
# The model results are gathered in one dataset, one row per simulation:
model_results.to_dataset(variable_names=["height", "reaction_forces"])

# %%
# Export a model result
# ---------------------
# A loaded model result is a ``ModelResult``. ``to_dict()`` exports its raw data, its
# inputs, outputs and metadata as in an archive, e.g. to serialize it or to hand it
# over to another program:
data = model_result.to_dict()
sorted(data)

# %%
data["inputs"]["height"]

# %%
# ``ModelResult.from_dict()`` rebuilds the result from this data:
ModelResult.from_dict(data).scalars(["height", "reaction_forces"])

# %%
# !!! note
#
#     Loading a model result needs the class of its model to be installed (its
#     plugin), to know its figures. The model itself is not executed.
