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
Explore a set of analysis node results
=============================

Filter the analysis node runs of a study, find which settings vary between them, group them
into families where a single setting varies, and spot the duplicates.
"""

# %%
from __future__ import annotations

import shutil

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
from vimseo.api import open_analysis_node_results
from vimseo.io.space_io import SpaceAnalysisNodeFileIO

# %%
# A study
# -------
# A convergence study of the design value of the reaction force of a beam: two DOE
# algorithms and three numbers of samples, with an analysis node run done twice and one done
# with another coverage of the tolerance interval.
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR
    / "archive/data_management/explore_analysis_nodes",
    "study_name": "design_value_study",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model("BendingTestAnalytical", "ThreePoints", **archive)
model.cache = None
parameter_space = (
    SpaceAnalysisNodeFileIO()
    .read(DESIGN_VALUE_LIB_DIR / "input_data" / "ElasticIsotropic_material_space.json")
    .parameter_space
)


def compute_design_value(**settings) -> None:
    """Compute the design value of the reaction force with some settings."""
    DesignValueAnalysisNode(**archive).execute(
        inputs=DesignValueInputs(model=model, parameter_space=parameter_space),
        settings=DesignValueSettings(output_names=["reaction_forces"], **settings),
    )


for algo in ("OT_MONTE_CARLO", "OT_LHS"):
    for n_samples in (5, 10, 20):
        compute_design_value(algo=algo, n_samples=n_samples)
compute_design_value(algo="OT_LHS", n_samples=10)
compute_design_value(algo="OT_LHS", n_samples=40, coverage=0.1)

# %%
# Open the analysis node results of a study
# --------------------------------
# ``open_analysis_node_results`` reads the summaries of the archive and returns a
# ``AnalysisNodeResults``, an immutable collection. A result is loaded only when it is used.
# The inputs of an analysis node run are its scalar settings and its outputs are its key values.
# The archive holds the design values and their sub-analysis nodes, the DOEs and the statistical
# analyses:
analysis_node_results = open_analysis_node_results(**archive)
analysis_node_results

# %%
# Filter
# ------
# The results of different analysis nodes cannot be compared: ``filter`` keeps those of the
# design value analysis node. ``failed=False`` drops the failed analysis node runs. ``ignoring``
# excludes a setting from the comparisons; it stays in the results:
design_values = analysis_node_results.filter(
    analysis_node_name="DesignValueAnalysisNode", failed=False
).ignoring("coverage")
len(design_values)

# %%
# What varies
# -----------
# ``varying_inputs`` lists the settings taking several values; ``coverage`` is left
# out, since the collection ignores it:
design_values.varying_inputs()

# %%
# Families along one setting
# --------------------------
# ``families(along=...)`` groups the analysis node runs which differ by this setting only. The
# key of a family is the value of the other varying settings. Since ``coverage`` is
# ignored, the analysis node run with 40 samples belongs to the family of ``OT_LHS``:
families = design_values.families(along="n_samples")
families

# %%
# The figures of the families show their key values versus the varying setting, here
# the mean and the standard deviation of the reaction force:
figures = families.visualize()
figures["scalar_outputs_vs_n_samples[algo=OT_LHS]"]

# %%
# Duplicates
# ----------
# Two analysis node runs with the same settings are reported, never deleted:
design_values.duplicates()[
    ["group", "analysis_node_run_id", "inputs.algo", "inputs.n_samples"]
]

# %%
# To a table
# ----------
# A query selects the analysis node runs on their settings, ``inputs.{name}``, and their key
# values, ``outputs.{name}``:
design_values.filter(query="`inputs.n_samples` >= 10").to_dataframe(
    variable_names=[
        "algo",
        "n_samples",
        "coverage",
        "mean.reaction_forces",
        "standard_deviation.reaction_forces",
    ]
)

# %%
# From an analysis node run to its sub-analysis nodes and its simulations
# ---------------------------------------------------
# ``children`` returns the analysis node runs of the sub-analysis nodes of an analysis node run, here a DOE and a
# statistical analysis:
analysis_node_run_id = design_values.summaries["analysis_node_run_id"][0]
analysis_node_results.children(analysis_node_run_id)

# %%
# ``model_results`` returns the simulations of the analysis node runs:
design_values[:1].model_results(**archive).to_dataframe(
    variable_names=["young_modulus", "nu_p", "reaction_forces"]
)
