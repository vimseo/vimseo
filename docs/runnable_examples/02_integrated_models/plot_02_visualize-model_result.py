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

# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Jorge CAMACHO-CASERO
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
#        :author: benedicte REINE
"""
Visualize and compare model results
===================================

Visualize model results and compare to other model results or reference data.
"""

# %%
from __future__ import annotations

import logging

from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.bars import BarPlot
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from numpy import atleast_1d
from pandas import DataFrame
from pandas import concat

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_result import ModelResult
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.utilities.plotting_utils import superpose_curves

activate_logger(level=logging.INFO)

# %%
# After execution, the results of a model can be visualized.
# The curves are shown by default:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/visualize_model_result",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/visualize_model_result",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/visualize_model_result/{model_name}_{load_case}_cache.hdf",
    ),
)
model.cache = None
model.execute()
result = ModelResult.from_data({
    "inputs": model.get_input_data(),
    "outputs": model.get_output_data(),
})
figs = model.plot_results(show=True, save=False)
figs["dplt_vs_dplt_grid"]

# %%
figs["moment_vs_moment_grid"]

# %%
# Scalar outputs can be visualized in a scatter matrix:
figs = model.plot_results(
    show=True,
    save=True,
    data="SCALARS",
    scalar_names=["young_modulus", "reaction_forces"],
)
figs["scalars"]

# %%
# Results can be obtained by querying the archive.
# For a ``DirectoryArchive``, the path to access to the current result is:
model.archive_manager.job_directory

# %%
# A result can be retrieved from this path:
result = ModelResult.from_data(
    model.archive_manager.get_result(model.archive_manager.job_directory)
)
print(result)

# %%
#

# %%
# Two model results can be compared. We first generate a second result:
model.execute({"young_modulus": atleast_1d(1.95e5), "imposed_dplt": atleast_1d(-10.0)})
result_1 = ModelResult.from_data({
    "inputs": model.get_input_data(),
    "outputs": model.get_output_data(),
})
result_1

# %%
# The scalars can be compared in a scatter matrix:
variable_names = ["young_modulus", "reaction_forces"]
df = DataFrame([
    result.get_numeric_scalars(variable_names=variable_names),
    result_1.get_numeric_scalars(variable_names=variable_names),
])
df["color"] = range(len(df))
plot = ScatterMatrix(Dataset.from_dataframe(df), coloring_variable="color")
plot.labels = ["result", "result 1"]
fig = plot.execute(
    save=False,
    show=True,
)
fig

# %%
# .. note::
#
#     Since the compared data are in a ``Pandas.DataFrame``,
#     other plotting library can be used, like ``Seaborn``:
#     ``sns.pairplot(df)``

# %%
# The curves can also be compared:
superpose_curves(
    [
        result.get_curve(("dplt_grid", "dplt")),
        result_1.get_curve(("dplt_grid", "dplt")),
    ],
    labels=["result", "result 1"],
)

# %%
# A model result can be compared to a data.
# A synthetic data is generated as a ``Pandas.DataFrame``:
df = DataFrame.from_dict({
    "young_modulus": atleast_1d(9e4),
    "nu_p": atleast_1d(0.25),
    "reaction_forces": atleast_1d(1e3),
})
variable_names = list(df.columns.values)

# %%
# The model result is added to the ``DataFrame``, and the latter is plotted:
df = concat(
    [
        df,
        DataFrame([result.get_numeric_scalars(variable_names=variable_names)]),
    ],
    ignore_index=True,
)

# %%
# The dataframe is plotted to compare the model result to the synthetic result.
# First, we compare with a bar plot:
plot = BarPlot(Dataset.from_dataframe(df))
plot.title = "Comparison of model result with data"
plot.font_size = 20
plot.labels = ["data", "model result"]
fig = plot.execute(save=True, show=True, file_format="html")[0]
fig

# %%
# And with a scatter matrix.
# For a small number of data to compare (two here), it is less relevant than the bar plot,
# It may become more interesting for a larger number of data to compare:
df["color"] = range(len(df))
plot = ScatterMatrix(Dataset.from_dataframe(df), coloring_variable="color")
plot.labels = ["data", "model result"]
fig = plot.execute(
    save=False,
    show=True,
)
fig

# %%
# Figures holding several lines
# -----------------------------
# The figures of a model are declared in its ``PLOTS`` class attribute, either as a
# tuple of variable names whose first one is the abscissa, or as a ``Plot`` object
# when the lines shall be styled, drawn against a secondary ordinate axis or
# completed with horizontal reference lines.
# The ``MockMultiCurves`` model declares one figure of each kind:
multi_curve_model = create_model(
    "MockMultiCurves",
    "Dummy",
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/visualize_model_result",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/visualize_model_result",
    ),
)
multi_curve_model.cache = None

for spec in multi_curve_model.plots:
    print(f"{spec.get_name()}: {[trace.get_label() for trace in spec.traces]}")

# %%
# Comparing variables within a result
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Several ordinates sharing an abscissa are drawn on a single figure. Here the
# three energies are declared as the plain tuple
# ``("displacement_history", "energy_strain_history", ...)``, and the colours are
# taken from the default palette. Since the axis holds several lines, it is
# labelled with the variable names and drawn in black:
multi_curve_model.execute()
multi_figs = multi_curve_model.plot_results(show=True, save=False)
multi_figs["energy_strain_history_and_2_more_vs_displacement_history"]

# %%
# When the quantities have different magnitudes, a line can be drawn against a
# secondary ordinate axis. This second figure is declared as a ``Plot`` object: the
# force keeps the left axis, the crack position moves to the right one, and a
# horizontal reference line shows the critical energy prescribed as a model input.
# Each axis takes the colour of its line when it holds a single one:
multi_figs["crack_propagation"]

# %%
# A subset of the lines can be drawn, by passing the ordinate names to keep.
# The figures of a result are available as ``ModelResult.plots``, which groups the
# curves per figure, while ``ModelResult.curves`` remains the flat list of all of
# them:
multi_result = ModelResult.from_data(
    {
        "inputs": multi_curve_model.get_input_data(),
        "outputs": multi_curve_model.get_output_data(),
    },
    model=multi_curve_model,
)
superpose_curves(
    multi_result.plots[0],
    variable_names=["energy_strain_history", "energy_damage_history"],
    show=True,
    save=False,
)

# %%
# Comparing a variable across results
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# A second result is generated with a larger imposed displacement:
multi_curve_model.execute({"max_displacement": atleast_1d(15.0)})
multi_result_1 = ModelResult.from_data(
    {
        "inputs": multi_curve_model.get_input_data(),
        "outputs": multi_curve_model.get_output_data(),
    },
    model=multi_curve_model,
)

# %%
# The same curve coming from both results is superposed, each one identified by
# its label:
curve_name = ("displacement_history", "force_history")
superpose_curves(
    [
        multi_result.get_curve(curve_name),
        multi_result_1.get_curve(curve_name),
    ],
    labels=["result", "result 1"],
    show=True,
    save=False,
)

# %%
# Whole figures can be superposed as well. In that case the colour identifies the
# result and the dash pattern identifies the variable, so that a given energy
# stays comparable from one result to the other:
superpose_curves(
    [multi_result.plots[0], multi_result_1.plots[0]],
    labels=["result", "result 1"],
    show=True,
    save=False,
)
