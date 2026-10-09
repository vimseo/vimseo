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
Archive the results of the tools in MLflow
==========================================

Archive the results of the tools in an MLflow database, search the tool runs and
navigate between the tool runs and their simulations.
"""

# %%
from __future__ import annotations

import json
import logging
import operator
import shutil

from mlflow.tracking import MlflowClient
from pandas import DataFrame

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.api import load_tool_result
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.storage_management.tool_archive import open_tool_archive
from vimseo.tools.design_value import DESIGN_VALUE_LIB_DIR
from vimseo.tools.design_value.design_value_tool import DesignValueInputs
from vimseo.tools.design_value.design_value_tool import DesignValueSettings
from vimseo.tools.design_value.design_value_tool import DesignValueTool
from vimseo.tools.doe.custom_doe import CustomDOETool

activate_logger(level=logging.WARNING)

# %%
# This example follows the one archiving the tool results in directories, with an
# MLflow database instead. The tools and the model archive their results in the same
# database, which is emptied first since the example is meant to be run repeatedly:
archive_root = EXAMPLE_RUNS_DIR / "archive/tool_result_management/mlflow"
shutil.rmtree(archive_root, ignore_errors=True)
# The working directories of the tools are created under ``root_directory``.
archive = {
    "archive_manager": "MlflowArchive",
    "archive_root": archive_root,
    "root_directory": EXAMPLE_RUNS_DIR / "tool_runs/tool_result_management/mlflow",
}

model = create_model(
    "BendingTestAnalytical",
    "ThreePoints",
    IntegratedModelSettings(
        archive_manager="MlflowArchive",
        directory_archive_root=archive_root,
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/tool_result_management",
        cache_file_path=archive_root / "BendingTestAnalytical_ThreePoints_cache.hdf",
    ),
)

# %%
# A design value is computed, then the samples of its DOE are replayed: the
# simulations of the replay are retrieved from the cache of the model.
parameter_space = (
    SpaceToolFileIO()
    .read(DESIGN_VALUE_LIB_DIR / "input_data" / "ElasticIsotropic_material_space.json")
    .parameter_space
)
design_value = DesignValueTool(**archive)
design_value.execute(
    inputs=DesignValueInputs(model=model, parameter_space=parameter_space),
    settings=DesignValueSettings(output_names=["reaction_forces"], n_samples=5),
)
samples = design_value._subtools["DOETool"].result.dataset
replay = CustomDOETool(**archive)
replay.execute(model=model, input_dataset=samples, output_names=["reaction_forces"])

# %%
# How a tool run is stored in MLflow
# ----------------------------------
# A tool run is an MLflow run of the experiment ``tools``, named after its tool. The
# run of a subtool is nested in the run of its parent tool. The simulations are in
# the experiment of their model, ``BendingTestAnalytical_ThreePoints``.
#
# The tool run is described by:
#
# - **tags** ``vimseo.*``: the ``tool_run_id``, the tool, the parent tool run, the class
#   of the result, the model, and the ``run_id`` of the simulations and of the child
#   tool runs,
# - **params**: the settings of the tool,
# - **metrics**: the few numbers summarizing the result, given by
#   :meth:`.BaseResult.get_key_values`, e.g. the mean and the standard deviation of
#   the reaction forces for a design value,
# - **artifacts**: the result in HDF5 format and its summary in JSON format,
# - the **description**, shown by the user interface, linking to the parent and
#   child tool runs and to the simulations.
#
# The archive provides the same interface as with directories:
tool_archive = open_tool_archive("MlflowArchive", archive_root)
summaries = sorted(tool_archive.search_tool_runs(), key=operator.itemgetter("datetime"))
DataFrame([
    {
        "tool": summary["tool_name"],
        "tool_run_id": summary["tool_run_id"][:8],
        "parent": summary["parent_tool_run_id"][:8],
        "simulations": len(summary.get("simulation_run_ids", [])),
        "mlflow run": summary["mlflow_run_id"][:8],
        "metrics": summary["key_values"],
    }
    for summary in summaries
])

# %%
# The database can also be queried with the MLflow client, bound to the tracking uri
# of the archive. For instance, the tool runs of the design values whose standard
# deviation of the reaction forces is lower than 100 N:
client = MlflowClient(tracking_uri=tool_archive.uri)
tools_experiment = client.get_experiment_by_name("tools")
runs = client.search_runs(
    [tools_experiment.experiment_id],
    filter_string=(
        "tags.`vimseo.tool_name` = 'DesignValueTool' "
        "and metrics.`standard_deviation.reaction_forces` < 100"
    ),
)
[(run.info.run_name, run.data.metrics) for run in runs]

# %%
# The description of the run of the design value links to its subtools and to its
# simulations, in the user interface of MLflow:
(design_value_run,) = runs
print(design_value_run.data.tags["mlflow.note.content"])

# %%
# From a tool run to its simulations
# ----------------------------------
# Each simulation records, in the tag ``vimseo.tool_run_ids``, all the tool runs which
# used it, including the ones which retrieved it from the cache: the filter below,
# also usable in the user interface, finds the simulations of the replay, though it
# did not run any of them.
simulations_experiment = client.get_experiment_by_name(
    "BendingTestAnalytical_ThreePoints"
)
replay_id = replay.result.metadata.tool_run_id
simulations = client.search_runs(
    [simulations_experiment.experiment_id],
    filter_string=f"tags.`vimseo.tool_run_ids` LIKE '%{replay_id}%'",
)
DataFrame([
    {
        "run_id": simulation.data.tags["run_id"][:8],
        "computed by": simulation.data.tags["tool_run_id"][:8],
        "used by": [
            i[:8] for i in json.loads(simulation.data.tags["vimseo.tool_run_ids"])
        ],
        "reaction_forces": simulation.data.metrics["reaction_forces"],
    }
    for simulation in simulations
])

# %%
# Conversely, the simulations are read back from the ``simulation_run_ids`` of a tool
# result with ``get_results_by_run_id``, which searches all the experiments of the
# archive of the model. In the user interface, a simulation is found by the filter
# ``tags.run_id = '{run_id}'``.
simulation_id = replay.result.metadata.simulation_run_ids[0]
(simulation,) = model.archive_manager.get_results_by_run_id([simulation_id])
simulation["inputs"]

# %%
# From a simulation to its tool runs
# ----------------------------------
runs_by_id = {summary["tool_run_id"]: summary for summary in summaries}
for tool_run_id in tool_archive.find_tool_runs_of_simulation(simulation_id):
    print(runs_by_id[tool_run_id]["tool_name"], tool_run_id[:8])

# %%
# Load an archived tool result
# ----------------------------
# A tool result is loaded from the id of its MLflow run with the URI ``runs:/{id}``,
# or from its ``tool_run_id`` with ``tool-run:{tool_run_id}`` when the archive of the
# configuration is an MLflow one:
result = load_tool_result(
    f"runs:/{design_value_run.info.run_id}", archive_root=archive_root
)
result.tabulate()["statistics"]

# %%
# The database is explored with the user interface of MLflow, launched by:
#
# .. code-block:: console
#
#     mlflow ui --backend-store-uri {tool_archive.uri}
#
# The tool runs are in the experiment ``tools``, where the runs of the subtools are
# unfolded under the runs of their parents.
print(f"mlflow ui --backend-store-uri {tool_archive.uri}")
