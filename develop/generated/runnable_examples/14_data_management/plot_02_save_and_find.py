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
Save and find the results
=========================

Where the results go, and how to list them without loading them.
"""

# %%
from __future__ import annotations

import shutil

from gemseo.algos.parameter_space import ParameterSpace
from pandas import DataFrame

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.api import search_model_results
from vimseo.api import search_tool_runs
from vimseo.tools.doe.doe import DOETool

# %%
# Where the results go
# --------------------
# Three settings, shared by the models and the tools, say where a result is saved:
#
# - ``archive_manager``: ``"DirectoryArchive"`` (the default) or ``"MlflowArchive"``,
# - ``directory_archive_root``: the root of the archive,
# - ``study_name``: the study grouping the runs inside the archive,
#   ``"default_study"`` by default (``VIMSEO_STUDY_NAME``).
#
# Their defaults come from the configuration, so that a script usually sets none of
# them. Here, two studies, one per layup, share one archive:
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR
    / "archive/data_management/save_and_find",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

parameter_space = ParameterSpace()
parameter_space.add_random_variable(
    "height", "OTUniformDistribution", minimum=30.0, maximum=60.0
)

for study_name in ["layup_A", "layup_B"]:
    model = create_model(
        "BendingTestAnalytical",
        "Cantilever",
        **archive,
        study_name=study_name,
        cache_file_path=archive["directory_archive_root"] / f"{study_name}_cache.hdf",
    )
    doe = DOETool(**archive, study_name=study_name)
    doe.execute(model=model, parameter_space=parameter_space, n_samples=3)

# %%
# Saving is automatic
# -------------------
# Nothing has to be called to save a result: each simulation and each tool run is
# archived when it ends. A simulation is archived when it starts too, with the status
# ``RUNNING``, so that a simulation interrupted by a crash stays visible. A simulation
# served by the cache of the model is not archived again.

# %%
# Find the model results
# ----------------------
# ``search_model_results`` returns one summary per simulation, from the oldest to the
# newest. An empty filter means every value; by default, every study is searched:
archived_model_runs = search_model_results(
    **archive, model_name="BendingTestAnalytical"
)
DataFrame(archived_model_runs)[["run_id", "study_name", "load_case", "tool_run_id"]]

# %%
# A query selects the simulations on their inputs, outputs and metadata, with ``and``,
# ``or`` and parentheses:
DataFrame(
    search_model_results(
        **archive,
        query="`inputs.height` < 40 or `outputs.reaction_forces` < -6000",
    )
)[["run_id", "study_name", "inputs.height", "outputs.reaction_forces"]]

# %%
# Find the tool results
# ---------------------
# ``search_tool_runs`` does the same for the tool runs, here in one study only:
archived_tool_runs = search_tool_runs(**archive, study_name="layup_A")
DataFrame(archived_tool_runs)[["tool_run_id", "tool_name", "status", "key_values"]]

# %%
# A summary carries the ``uri`` of its result, used to load it: see the next example.
