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
Tool results in directories
===========================

How a ``DirectoryArchive`` stores the tool runs: their directories, the tree of the
tool runs and their subtools, and the links between the tool runs and the simulations.
"""

# %%
from __future__ import annotations

import shutil

from pandas import DataFrame

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.api import load_model_results
from vimseo.api import load_tool_results
from vimseo.api import open_tool_archive
from vimseo.api import search_tool_runs
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.tools.design_value import DESIGN_VALUE_LIB_DIR
from vimseo.tools.design_value.design_value_tool import DesignValueInputs
from vimseo.tools.design_value.design_value_tool import DesignValueSettings
from vimseo.tools.design_value.design_value_tool import DesignValueTool
from vimseo.tools.doe.custom_doe import CustomDOETool

# %%
# The tool runs
# -------------
# A design value executes two subtools: a DOE, which runs the simulations, and a
# statistical analysis. The subtools inherit the archive settings of their parent.
# The samples of the DOE are then replayed: the simulations come from the cache of the
# model, and are shared by the two tool runs.
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR
    / "archive/data_management/tool_directory",
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
    SpaceToolFileIO()
    .read(DESIGN_VALUE_LIB_DIR / "input_data" / "ElasticIsotropic_material_space.json")
    .parameter_space
)
design_value = DesignValueTool(**archive)
design_value.execute(
    inputs=DesignValueInputs(model=model, parameter_space=parameter_space),
    settings=DesignValueSettings(output_names=["reaction_forces"], n_samples=5),
)

# %%
# The DOE of the design value is a tool run of its own, whose result holds the
# samples:
(doe_run,) = search_tool_runs(**archive, tool_name="DOETool")
samples = load_tool_results(doe_run["tool_run_id"], **archive)[0].dataset
replay = CustomDOETool(**archive)
replay.execute(model=model, input_dataset=samples, output_names=["reaction_forces"])

# %%
# The archive manager of the tools
# --------------------------------
# It summarizes each tool run without loading its result, from the oldest to the
# newest. The ``key_values`` are the few numbers summarizing a result
# (:meth:`.BaseResult.get_key_values`):
tool_archive_manager = open_tool_archive(**archive)
archived_tool_runs = search_tool_runs(**archive)
DataFrame([
    {
        "tool": run["tool_name"],
        "tool_run_id": run["tool_run_id"],
        "parent": run["parent_tool_run_id"],
        "simulations": len(run.get("simulation_run_ids", [])),
        "key_values": run.get("key_values"),
    }
    for run in archived_tool_runs
])


# %%
# The parent and child tool runs form a tree:
def print_tree(parent_id: str = "", indent: str = "") -> None:
    for run in archived_tool_runs:
        if run["parent_tool_run_id"] == parent_id:
            print(f"{indent}- {run['tool_name']} {run['tool_run_id']}")
            print_tree(run["tool_run_id"], indent + "    ")


print_tree()

# %%
# A tool run is a directory ``{root}/{study}/tools/{tool_name}/{tool_run_id}``,
# holding the result in HDF5 format and its summary in JSON format:
tool_run_id = design_value.result.metadata.tool_run_id
run_directory = (
    archive["directory_archive_root"]
    / "my_study"
    / "tools"
    / "DesignValueTool"
    / tool_run_id
)
sorted(path.name for path in run_directory.iterdir())

# %%
# Load a tool result
# ------------------
# By its ``tool_run_id`` or by its URI; here, the directory of the tool run is a URI
# too:
tool_result = load_tool_results(tool_run_id, **archive)[0]
tool_result = load_tool_results(run_directory, **archive)[0]

# %%
# From a tool run to its simulations
# ----------------------------------
metadata = tool_result.metadata
print("child tool runs:", metadata.child_tool_run_ids)
model_results = load_model_results(metadata.simulation_run_ids, **archive)
model_results.to_dataframe(["young_modulus", "reaction_forces"])

# %%
# From a simulation to its tool runs
# ----------------------------------
# A simulation is used by every tool run which retrieved it, from a run or from the
# cache: the design value, its DOE and the replay.
runs_by_id = {run["tool_run_id"]: run for run in archived_tool_runs}
for other_id in tool_archive_manager.find_tool_runs_of_simulation(
    metadata.simulation_run_ids[0]
):
    print(runs_by_id[other_id]["tool_name"], other_id)
