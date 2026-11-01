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
The roundtrip of the results
============================

Generate, save, load and plot the results of a model and of an analysis node.
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

# %%
# Choose where
# ------------
# The results are archived automatically. The archive is chosen by three settings, the
# same for a model, an analysis node and every function reading the archive:
archive = {
    "archive_manager": "DirectoryArchive",  # or "MlflowArchive": nothing else changes
    "directory_archive_root": EXAMPLE_RUNS_DIR / "archive/data_management/roundtrip",
    "study_name": "roundtrip",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

# %%
# Generate and save
# -----------------
# A model result is saved at each execution of the model, an analysis node result at each
# execution of the analysis node:
model = create_model(
    "BendingTestAnalytical",
    "Cantilever",
    **archive,
    cache_file_path=archive["directory_archive_root"] / "cache.hdf",
)
model.execute()

parameter_space = ParameterSpace()
parameter_space.add_random_variable(
    "height", "OTUniformDistribution", minimum=30.0, maximum=60.0
)
doe = DOEAnalysisNode(**archive)
doe.execute(model=model, parameter_space=parameter_space, n_samples=5)

# %%
# Find
# ----
# Each result is summarized without being loaded; the summaries are sorted from the
# oldest to the newest:
archived_model_runs = search_model_results(
    **archive, model_name="BendingTestAnalytical"
)
archived_analysis_node_runs = search_analysis_node_runs(
    **archive, analysis_node_name="DOEAnalysisNode"
)

# %%
# Load
# ----
# A summary carries the ``uri`` of its result, from which it is loaded. Neither the
# model nor the analysis node is needed. A loading function takes one reference or many, and
# returns a collection; ``[0]`` gives the first result:
model_result = load_model_results(archived_model_runs[0]["uri"], **archive)[0]
analysis_node_result = load_analysis_node_results(
    archived_analysis_node_runs[0]["uri"], **archive
)[0]

# %%
# Plot
# ----
# Both kinds of results draw their figures and give their values as tables:
model_figures = model_result.plot()
analysis_node_figures = analysis_node_result.plot()
analysis_node_result.to_dataframes()

# %%
# The API in one table
# --------------------
#
# | Step | Model results | Analysis node results |
# | --- | --- | --- |
# | Choose where | `create_model(..., **archive)` | `Analysis node(**archive)` |
# | Generate and save | `model.execute()` | `analysis_node.execute()` |
# | Find | `search_model_results(**archive)` | `search_analysis_node_runs(**archive)` |
# | Load | `load_model_results(ref or refs, **archive)` | `load_analysis_node_results(ref or refs, **archive)` |
# | Plot | `model_result.plot()` | `analysis_node_result.plot()` |
# | Tabulate | `model_result.to_dataframes()`, `model_results.to_dataset()` | `analysis_node_result.to_dataframes()` |
# | Explore a set | `open_model_results(**archive).filter(...).families(along=...)` | `open_analysis_node_results(**archive).filter(...)` |
# | Dashboards | `dashboard_results` (`vimseo-dashboards`), `dashboard_mlflow` | `dashboard_results` (`vimseo-dashboards`), `dashboard_mlflow` |
#
# ``archive`` holds ``archive_manager``, ``directory_archive_root`` and
# ``study_name``.
