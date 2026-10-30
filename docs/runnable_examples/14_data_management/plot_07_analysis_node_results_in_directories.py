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
Analysis node results in directories
===========================

How a ``DirectoryArchive`` stores the analysis node runs: their directories, the tree of the
analysis node runs and their sub-analysis nodes, and the links between the analysis node runs and the simulations.
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
from vimseo.analysis_nodes.doe.custom_doe import CustomDOEAnalysisNode
from vimseo.api import create_model
from vimseo.api import load_analysis_node_results
from vimseo.api import load_model_results
from vimseo.api import open_analysis_node_archive
from vimseo.api import search_analysis_node_runs
from vimseo.io.space_io import SpaceAnalysisNodeFileIO

# %%
# The analysis node runs
# -------------
# A design value executes two sub-analysis nodes: a DOE, which runs the simulations, and a
# statistical analysis. The sub-analysis nodes inherit the archive settings of their parent.
# The samples of the DOE are then replayed: the simulations come from the cache of the
# model, and are shared by the two analysis node runs.
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR
    / "archive/data_management/analysis_node_directory",
    "study_name": "my_study",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model(
    "BendingTestAnalytical",
    "ThreePoints",
    **archive,
    cache_file_path=archive["directory_archive_root"] / "cache.hdf",
)
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
# The DOE of the design value is an analysis node run of its own, whose result holds the
# samples:
(doe_run,) = search_analysis_node_runs(**archive, analysis_node_name="DOEAnalysisNode")
samples = load_analysis_node_results(doe_run["analysis_node_run_id"], **archive)[
    0
].dataset
replay = CustomDOEAnalysisNode(**archive)
replay.execute(model=model, input_dataset=samples, output_names=["reaction_forces"])

# %%
# The archive manager of the analysis nodes
# --------------------------------
# It summarizes each analysis node run without loading its result, from the oldest to the
# newest. The ``key_values`` are the few numbers summarizing a result
# (:meth:`.BaseResult.get_key_values`):
analysis_node_archive_manager = open_analysis_node_archive(**archive)
archived_analysis_node_runs = search_analysis_node_runs(**archive)
DataFrame([
    {
        "analysis_node": run["analysis_node_name"],
        "analysis_node_run_id": run["analysis_node_run_id"],
        "parent": run["parent_analysis_node_run_id"],
        "simulations": len(run.get("simulation_run_ids", [])),
        "key_values": run.get("key_values"),
    }
    for run in archived_analysis_node_runs
])


# %%
# The parent and child analysis node runs form a tree:
def print_tree(parent_id: str = "", indent: str = "") -> None:
    for run in archived_analysis_node_runs:
        if run["parent_analysis_node_run_id"] == parent_id:
            print(
                f"{indent}- {run['analysis_node_name']} {run['analysis_node_run_id']}"
            )
            print_tree(run["analysis_node_run_id"], indent + "    ")


print_tree()

# %%
# An analysis node run is a directory ``{root}/{study}/analysis_nodes/{analysis_node_name}/{analysis_node_run_id}``,
# holding the result in HDF5 format and its summary in JSON format:
analysis_node_run_id = design_value.result.metadata.analysis_node_run_id
run_directory = (
    archive["directory_archive_root"]
    / "my_study"
    / "analysis_nodes"
    / "DesignValueAnalysisNode"
    / analysis_node_run_id
)
sorted(path.name for path in run_directory.iterdir())

# %%
# Load an analysis node result
# ------------------
# By its ``analysis_node_run_id`` or by its URI; here, the directory of the analysis node run is a URI
# too:
analysis_node_result = load_analysis_node_results(analysis_node_run_id, **archive)[0]
analysis_node_result = load_analysis_node_results(run_directory, **archive)[0]

# %%
# From an analysis node run to its simulations
# ----------------------------------
metadata = analysis_node_result.metadata
print("child analysis node runs:", metadata.child_analysis_node_run_ids)
model_results = load_model_results(metadata.simulation_run_ids, **archive)
model_results.to_dataframe(["young_modulus", "reaction_forces"])

# %%
# From a simulation to its analysis node runs
# ----------------------------------
# A simulation is used by every analysis node run which retrieved it, from a run or from the
# cache: the design value, its DOE and the replay.
runs_by_id = {run["analysis_node_run_id"]: run for run in archived_analysis_node_runs}
for other_id in analysis_node_archive_manager.find_analysis_node_runs_of_simulation(
    metadata.simulation_run_ids[0]
):
    print(runs_by_id[other_id]["analysis_node_name"], other_id)
