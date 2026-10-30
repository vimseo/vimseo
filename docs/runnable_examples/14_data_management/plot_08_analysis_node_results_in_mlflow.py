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
Analysis node results in MLflow
======================

How an ``MlflowArchive`` stores the analysis node runs: nested runs in the experiment of the
study, the mapping to tags, params, metrics and artifacts, and the queries.

This example needs the ``mlflow`` extra.
"""

# %%
from __future__ import annotations

import shutil

from pandas import DataFrame

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.analysis_nodes.design_value import DESIGN_VALUE_LIB_DIR
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueAnalysisNode,
)
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueInputs,
)
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueSettings,
)
from vimseo.api import create_model
from vimseo.api import load_analysis_node_results
from vimseo.api import load_model_results
from vimseo.api import open_analysis_node_archive
from vimseo.api import search_analysis_node_runs
from vimseo.io.space_io import SpaceAnalysisNodeFileIO
from vimseo.utilities.optional_dependencies import import_optional

mlflow_tracking = import_optional("mlflow.tracking", "mlflow")

# %%
# The analysis node runs
# -------------
# The code is the one of the previous example, with ``archive_manager="MlflowArchive"``:
archive = {
    "archive_manager": "MlflowArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR
    / "archive/data_management/analysis_node_mlflow",
    "study_name": "my_study",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model("BendingTestAnalytical", "ThreePoints", **archive)
model.cache = None
parameter_space = (
    SpaceAnalysisNodeFileIO()
    .read(DESIGN_VALUE_LIB_DIR / "input_data" / "ElasticIsotropic_material_space.json")
    .parameter_space
)
design_value = DesignValueAnalysisNode(**archive)
design_value.execute(
    inputs=DesignValueInputs(model=model, parameter_space=parameter_space),
    settings=DesignValueSettings(output_names=["reaction_forces"], n_samples=5),
)

# %%
# How an analysis node run is stored in MLflow
# ----------------------------------
# An analysis node run is an MLflow run of the experiment of its study, next to the simulations,
# with the tag ``vimseo.kind=analysis_node_run``. The run of a sub-analysis node is nested in the run of
# its parent. An analysis node run is described by:
#
# - **tags** ``vimseo.*``: the ``analysis_node_run_id``, the analysis node, the study, the parent analysis node
#   run, the class of the result, and the ``run_id`` of the simulations,
# - **params**: the settings of the analysis node,
# - **metrics**: the key values of the result, e.g. the mean of the reaction forces,
# - **artifacts**: the result in HDF5 format and its summary in JSON format,
# - the **description**, linking to the parent, the children and the simulations.
#
# The searches are the same as with directories:
archived_analysis_node_runs = search_analysis_node_runs(**archive)
DataFrame(archived_analysis_node_runs)[
    ["analysis_node_name", "analysis_node_run_id", "uri", "key_values"]
]

# %%
# Load an analysis node result
# ------------------
# By its ``analysis_node_run_id`` or by its URI, here ``runs:/{mlflow_run_id}``, the Run ID shown
# by the user interface of MLflow:
analysis_node_run_id = design_value.result.metadata.analysis_node_run_id
analysis_node_result = load_analysis_node_results(analysis_node_run_id, **archive)[0]

uri = next(
    run["uri"]
    for run in archived_analysis_node_runs
    if run["analysis_node_run_id"] == analysis_node_run_id
)
analysis_node_result = load_analysis_node_results(uri, **archive)[0]

# %%
# Its simulations are loaded as with directories:
model_results = load_model_results(
    analysis_node_result.metadata.simulation_run_ids, **archive
)
len(model_results)

# %%
# Queries
# -------
# A query of ``search_analysis_node_runs`` reads the settings as ``inputs.{name}`` and the key
# values as ``outputs.{name}``, e.g. the design values whose standard deviation of the
# reaction forces is lower than 100 N:
[
    run["analysis_node_run_id"]
    for run in search_analysis_node_runs(
        **archive,
        analysis_node_name="DesignValueAnalysisNode",
        query="`outputs.standard_deviation.reaction_forces` < 100",
    )
]

# %%
# The MLflow client of the archive filters on the tags and the metrics too; the same
# filter works in the user interface:
analysis_node_archive_manager = open_analysis_node_archive(**archive)
client = mlflow_tracking.MlflowClient(tracking_uri=analysis_node_archive_manager.uri)
experiment = client.get_experiment_by_name("my_study")
runs = client.search_runs(
    [experiment.experiment_id],
    filter_string="tags.`vimseo.kind` = 'analysis_node_run' "
    "and tags.`vimseo.analysis_node_name` = 'DesignValueAnalysisNode' "
    "and metrics.`standard_deviation.reaction_forces` < 100",
)
[run.data.tags["vimseo.analysis_node_run_id"] for run in runs]

# %%
# The simulations used by an analysis node run, including the ones retrieved from the cache,
# carry its ``analysis_node_run_id`` in their tag ``vimseo.analysis_node_run_ids``:
simulations = client.search_runs(
    [experiment.experiment_id],
    filter_string=f"tags.`vimseo.kind` = 'simulation' "
    f"and tags.`vimseo.analysis_node_run_ids` LIKE '%{analysis_node_run_id}%'",
)
len(simulations)

# %%
# The user interface
# ------------------
# ``dashboard_mlflow`` opens the user interface of MLflow. The study is one experiment;
# the analysis node runs are shown as a tree, and ``tags.vimseo.kind = 'analysis_node_run'`` hides the
# simulations.
