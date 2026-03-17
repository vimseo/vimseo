# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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
from vimseo.utilities.plotting_utils import plot_curves

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
model.archive_manager._accept_overwrite_job_dir = True
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
plot_curves(
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
