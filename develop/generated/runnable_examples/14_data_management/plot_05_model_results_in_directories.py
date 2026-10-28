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
Model results in directories
============================

How a ``DirectoryArchive`` stores the simulations: the layout of the directories, the
job name, the status, the persistent files, and a cache rebuilt from the archive.
"""

# %%
from __future__ import annotations

import shutil
from pathlib import Path

from numpy import atleast_1d
from pandas import DataFrame

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.api import load_model_results
from vimseo.api import search_model_results
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.storage_management.base_storage_manager import PersistencyPolicy

# %%
# Scratch, archive and cache
# --------------------------
# Three places hold the data of a simulation:
#
# - the **scratch**: the files of an external solver, disposable,
# - the **archive**: the inputs, the outputs and the metadata to keep, and the files
#   the model declares persistent, copied from the scratch,
# - the **cache**: an HDF5 file avoiding to run a simulation twice; it can be rebuilt
#   from the archive. A simulation served by the cache is not archived again.
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR
    / "archive/data_management/model_directory",
    "study_name": "my_study",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model(
    "MockModelPersistent",
    "LC1",
    IntegratedModelSettings(
        **archive,
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/data_management",
        directory_scratch_persistency=PersistencyPolicy.DELETE_NEVER,
    ),
)
model.cache = None
model.execute({"x1": atleast_1d(2.0), "x2": atleast_1d(-2.0)})
model.execute({"x1": atleast_1d(3.0), "x2": atleast_1d(-1.0)})

# %%
# The layout of the archive
# -------------------------
# A simulation is a directory ``{root}/{study}/{model}/{load_case}/{job}``, named by
# its ``run_id``: a path gives the identifier, an identifier gives the path. The
# ``run_id`` starts with the UTC date of the simulation, so that sorting the
# directories sorts the simulations chronologically.
#
# | Setting | Path of a simulation | Second execution |
# | --- | --- | --- |
# | default | `{root}/default_study/{model}/{load_case}/{run_id}` | a new directory, named by the new `run_id` |
# | `study_name="my_study"` | `{root}/my_study/{model}/{load_case}/{run_id}` | `{root}/my_study/{model}/{load_case}/{other_run_id}` |
# | `job_name="my_job"` | `{root}/default_study/{model}/{load_case}/my_job` | the same directory: fails, unless overwriting is accepted |
#
# The study of a model is changed between two executions with
# ``model.archive_manager.set_study_name("other_study")``.
archived_model_runs = search_model_results(**archive)
job_directory = Path(archived_model_runs[0]["uri"])
job_directory.relative_to(archive["directory_archive_root"])

# %%
sorted(path.name for path in job_directory.iterdir())

# %%
# The JSON file holds the inputs, the outputs and the metadata, among which the
# ``status`` of the simulation: ``RUNNING`` from its start, then ``FINISHED`` or
# ``FAILED``. The other files are the persistent files of the model.

# %%
# Find and load
# -------------
# The summaries come from the metadata of the JSON files; the ``uri`` is the job
# directory:
DataFrame(archived_model_runs)[["run_id", "study_name", "model_name", "status", "uri"]]

# %%
# The job directory is a reference of its model result, as is its ``run_id``:
model_result = load_model_results(job_directory, **archive)[0]
model_result = load_model_results(archived_model_runs[0]["run_id"], **archive)[0]
(model_result.run_id, model_result.status, model_result.scalars(group="outputs"))

# %%
# A cache rebuilt from the archive
# --------------------------------
# A cache becomes unusable after a change of the model, or when it mixes successful and
# failed simulations. A new cache is rebuilt from the finished simulations of the
# current study, model and load case:
cache_from_archive = model.create_cache_from_archive()
print(cache_from_archive)
