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
Archive the results of the tools in directories
===============================================

Archive the results of the tools, find the simulations of a tool run and the tool runs
of a simulation, and load an archived result.
"""

# %%
from __future__ import annotations

import logging
import operator
import shutil

from pandas import DataFrame

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.api import load_simulation_results
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
# Two kinds of runs are identified by unique identifiers:
#
# - each execution of a model is a *simulation*, identified by its ``run_id``,
# - each execution of a tool is a *tool run*, identified by its ``tool_run_id``,
#   stored in the metadata of its result: ``result.metadata.tool_run_id``.
#
# The result of a tool run is archived, as the simulations of a model are, and the
# archive keeps the links between them:
#
# - a tool run knows the simulations it used, through their ``run_id``,
#   including the ones retrieved from the cache of the model,
# - a tool run executed by another tool, like the DOE of a design value, knows its
#   parent tool run, and the parent knows its children.
#
# The archive of the tool results is selected by the ``archive_manager`` setting of a
# tool, ``"DirectoryArchive"`` or ``"MlflowArchive"``, and its location by
# ``archive_root``. By default, they are the ones of the configuration
# (``tool_archive_manager``, else ``run_archive_manager``). The subtools of a tool
# archive their results with it.
#
# Here, the tools and the model archive their results in the same directory, which is
# emptied first since the example is meant to be run repeatedly:
archive_root = EXAMPLE_RUNS_DIR / "archive/tool_result_management/directory"
shutil.rmtree(archive_root, ignore_errors=True)
# The working directories of the tools are created under ``root_directory``.
archive = {
    "archive_manager": "DirectoryArchive",
    "archive_root": archive_root,
    "root_directory": EXAMPLE_RUNS_DIR / "tool_runs/tool_result_management/directory",
}

model = create_model(
    "BendingTestAnalytical",
    "ThreePoints",
    IntegratedModelSettings(
        archive_manager="DirectoryArchive",
        directory_archive_root=archive_root,
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/tool_result_management",
        cache_file_path=archive_root / "BendingTestAnalytical_ThreePoints_cache.hdf",
    ),
)

# %%
# A design value of the reaction forces is computed for an uncertain material. The
# :class:`.DesignValueTool` executes two subtools: a DOE, which runs the simulations,
# and a statistical analysis of their outputs:
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
# Then, the samples of this DOE are replayed by a :class:`.CustomDOETool`. Its
# simulations are retrieved from the cache of the model: they are not run again, and
# they are shared by the two tool runs.
samples = design_value._subtools["DOETool"].result.dataset
replay = CustomDOETool(**archive)
replay.execute(model=model, input_dataset=samples, output_names=["reaction_forces"])

# %%
# The archive of the tool results
# -------------------------------
# The archive is opened from its manager and its root, as a reader would do.
# Each tool run is summarized without loading its result: its tool, its status,
# its parent and its simulations. The ``key_values`` are the few numbers summarizing
# the result (see :meth:`.BaseResult.get_key_values`).
tool_archive = open_tool_archive("DirectoryArchive", archive_root)
summaries = sorted(tool_archive.search_tool_runs(), key=operator.itemgetter("datetime"))
DataFrame([
    {
        "tool": summary["tool_name"],
        "status": summary["status"],
        "tool_run_id": summary["tool_run_id"][:8],
        "parent": summary["parent_tool_run_id"][:8],
        "simulations": len(summary.get("simulation_run_ids", [])),
        "key_values": summary.get("key_values"),
    }
    for summary in summaries
])

# %%
# The parent and child tool runs form a tree:
runs_by_id = {summary["tool_run_id"]: summary for summary in summaries}


def print_tree(parent_id: str = "", indent: str = "") -> None:
    for summary in summaries:
        if summary["parent_tool_run_id"] == parent_id:
            print(f"{indent}- {summary['tool_name']} {summary['tool_run_id'][:8]}")
            print_tree(summary["tool_run_id"], indent + "    ")


print_tree()

# %%
# A tool run is a directory ``{root}/tools/{tool_name}/{tool_run_id}``, holding the
# result in HDF5 format and the summary in JSON format:
design_value_id = design_value.result.metadata.tool_run_id
run_directory = archive_root / "tools" / "DesignValueTool" / design_value_id
sorted(path.name for path in run_directory.iterdir())

# %%
# From a tool run to its simulations
# ----------------------------------
# The result of a tool run, read from the archive, is the same as the result of the
# tool. Its metadata give the ``tool_run_id`` of its tool run and of its children,
# and the ``run_id`` of its simulations:
result = tool_archive.get_tool_result(design_value_id)
metadata = result.metadata
print("tool_run_id:", metadata.tool_run_id)
print("tool_run_id of the children:", metadata.child_tool_run_ids)
print("run_id of the simulations:", metadata.simulation_run_ids)

# %%
# The simulations are in the archive of the model, where they are identified by the
# same ``run_id``. They are read back from it with ``get_results_by_run_id``, which
# searches the whole archive:
simulations = model.archive_manager.get_results_by_run_id(metadata.simulation_run_ids)
DataFrame([
    {
        "run_id": str(simulation["outputs"]["run_id"][0])[:8],
        "young_modulus": simulation["inputs"]["young_modulus"][0],
        "reaction_forces": simulation["outputs"]["reaction_forces"][0],
    }
    for simulation in simulations
])

# %%
# The simulations can also be loaded without creating their model, as
# :class:`.ModelResult`, from the archive manager and the root of their archive:
model_results = load_simulation_results(
    metadata.simulation_run_ids,
    archive_manager="DirectoryArchive",
    archive_root=archive_root,
)
model_results[0].get_numeric_scalars(
    variable_names=["young_modulus", "reaction_forces"]
)

# %%
# From a simulation to its tool runs
# ----------------------------------
# A simulation is used by all the tool runs which retrieved it, from a run or from the
# cache: the design value, its DOE and the replay of the DOE.
simulation_id = metadata.simulation_run_ids[0]
for tool_run_id in tool_archive.find_tool_runs_of_simulation(simulation_id):
    print(runs_by_id[tool_run_id]["tool_name"], tool_run_id[:8])

# %%
# Load an archived tool result
# ----------------------------
# A tool result is also loaded from a URI, without knowing its tool: the path to a
# result file, the directory of a tool run, or ``tool-run:{tool_run_id}`` in an
# archive. The command ``visualize_tool_result --uri ...`` writes its figures and
# tables in a directory, and the dashboard ``dashboard_tool_result`` explores it.
result = load_tool_result(f"tool-run:{design_value_id}", archive_root=archive_root)
result.tabulate()["statistics"]
