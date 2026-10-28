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
Model results in MLflow
=======================

How an ``MlflowArchive`` stores the simulations: one experiment per study, the mapping
of the data to the metrics, params and tags of MLflow, and the queries.

This example needs the ``mlflow`` extra.
"""

# %%
from __future__ import annotations

import shutil

from numpy import atleast_1d
from pandas import DataFrame

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.api import load_model_results
from vimseo.api import search_model_results
from vimseo.utilities.optional_dependencies import import_optional

mlflow_tracking = import_optional("mlflow.tracking", "mlflow")

# %%
# The archive
# -----------
# The code is the one of the previous example, with ``archive_manager="MlflowArchive"``.
# ``directory_archive_root`` is the directory of a local MLflow database; a remote
# server is set in the configuration (``VIMSEO_DATABASE__MODE=Team``), and then
# ``directory_archive_root`` is ignored.
archive = {
    "archive_manager": "MlflowArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR / "archive/data_management/model_mlflow",
    "study_name": "my_study",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model("BendingTestAnalytical", "Cantilever", **archive)
model.cache = None
for height in [40.0, 50.0, 60.0]:
    model.execute({"height": atleast_1d(height)})

# %%
# How a simulation is stored in MLflow
# ------------------------------------
# A study is one MLflow experiment, holding the simulations of all its models and its
# tool runs. A simulation is an MLflow run, named by its ``run_id``, with:
#
# - **metrics**: the numbers among the inputs and the outputs
#   (``inputs.height``, ``reaction_forces``),
# - **params**: the other inputs and outputs, as JSON,
# - **tags**: the metadata, and ``vimseo.kind=simulation``, ``vimseo.model``,
#   ``vimseo.load_case``, ``vimseo.run_id`` to tell the runs of a study apart.
#
# The run is created when the simulation starts, with the status ``RUNNING``.

# %%
# Find and load
# -------------
# The VIMSEO functions are the same as for a ``DirectoryArchive``; the ``uri`` is
# ``runs:/{mlflow_run_id}``:
archived_model_runs = search_model_results(**archive)
DataFrame(archived_model_runs)[["run_id", "study_name", "inputs.height", "uri"]]

# %%
# A query is the same for both archives, with ``or`` too, which the filters of MLflow
# do not support: the part joined by ``and`` is evaluated by the MLflow server, the
# rest by VIMSEO:
DataFrame(
    search_model_results(
        **archive,
        query="`inputs.height` > 45 and (`inputs.height` < 55 or status == 'FAILED')",
    )
)[["run_id", "inputs.height"]]

# %%
# ``runs:/`` also names the tool runs: loading the run of a tool run with
# ``load_model_results`` raises an error naming ``load_tool_results``.
model_result = load_model_results(archived_model_runs[0]["uri"], **archive)[0]
figures = model_result.plot()

# %%
# Queries of MLflow
# -----------------
# The MLflow client of the archive filters on any metric, param or tag; the same
# filter works in the user interface:
client = mlflow_tracking.MlflowClient(tracking_uri=model.archive_manager.uri)
experiment = client.get_experiment_by_name("my_study")
runs = client.search_runs(
    [experiment.experiment_id],
    filter_string="tags.`vimseo.kind` = 'simulation' and metrics.`inputs.height` > 45",
)
sorted(run.data.tags["vimseo.run_id"] for run in runs)

# %%
# A cache rebuilt from the archive
# --------------------------------
# As with directories, only the finished simulations of the current study, model and
# load case are used:
print(model.create_cache_from_archive())

# %%
# The user interface
# ------------------
# ``dashboard_mlflow`` opens the user interface of MLflow on the archive set in the
# configuration (``VIMSEO_DATABASE__*``), not on the ``directory_archive_root`` of this
# example; for the latter, run ``mlflow ui --backend-store-uri {model.archive_manager.uri}``.
# A study is one experiment; filter it with
# ``tags.vimseo.model = 'BendingTestAnalytical'``.
