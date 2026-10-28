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
Explore a set of results
========================

Filter the simulations of a study, find what varies between them, group them into
families where a single input varies, and spot the duplicates.
"""

# %%
from __future__ import annotations

import shutil

from numpy import atleast_1d

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.api import open_model_results

# %%
# A study
# -------
# A study of a beam: three heights and two widths, with a simulation run twice and one
# run with another numerical setting.
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR / "archive/data_management/explore",
    "study_name": "beam_study",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model("BendingTestAnalytical", "Cantilever", **archive)
model.cache = None
for width in (20.0, 30.0):
    for height in (30.0, 40.0, 50.0):
        model.execute({"height": atleast_1d(height), "width": atleast_1d(width)})
model.execute({"height": atleast_1d(40.0), "width": atleast_1d(20.0)})
model.execute({
    "height": atleast_1d(60.0),
    "width": atleast_1d(25.0),
    "imposed_dplt": atleast_1d(-4.0),
})

# %%
# Open the results of a study
# ---------------------------
# ``open_model_results`` reads the summaries of the archive and returns a
# ``ModelResults``, an immutable collection. A result is loaded only when it is used:
model_results = open_model_results(**archive)
model_results

# %%
# Filter
# ------
# ``filter`` keeps the results matching every condition and returns a new collection.
# ``failed=False`` drops the failed simulations (a status other than ``FINISHED``, or a
# positive ``error_code``). ``ignoring`` excludes a numerical setting from the
# comparisons; it stays in the results:
results_for_convergence = model_results.filter(
    model_name="BendingTestAnalytical", failed=False
).ignoring("imposed_dplt")
len(results_for_convergence)

# %%
# What varies
# -----------
# ``varying_inputs`` lists the inputs taking several values; ``imposed_dplt`` is left
# out, since the collection ignores it:
results_for_convergence.varying_inputs()

# %%
# Families along one input
# ------------------------
# ``families(along=...)`` groups the results which differ by this input only. The key
# of a family is the value of the other varying inputs; the results alone in their
# group are reported:
families = results_for_convergence.families(along="height")
families

# %%
# A family is a collection, which superposes the curves of its results, labelled by
# the value of the varying input:
family = families.get(width=20.0)
family.visualize(plot_names=["moment_vs_moment_grid"])["moment_vs_moment_grid"]

# %%
# The figures of all the families show their scalar outputs versus the varying input:
figures = families.visualize()
figures["scalar_outputs_vs_height[width=20.0]"]

# %%
# Duplicates
# ----------
# Two simulations with the same inputs are reported, never deleted:
results_for_convergence.duplicates()[
    ["group", "run_id", "inputs.height", "inputs.width"]
]

# %%
# To a table
# ----------
# A query selects the results with ``and``, ``or`` and parentheses, the inputs being
# ``inputs.{name}`` and the outputs ``outputs.{name}``; it is the same for both
# archives:
results_for_convergence.filter(
    query="`inputs.height` < 35 or `outputs.reaction_forces` < -4000"
).to_dataframe(variable_names=["height", "width", "reaction_forces"])
