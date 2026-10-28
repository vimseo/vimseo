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
Plot the results
================

Draw the figures and the tables of a model result and of a tool result, from Python
and from the dashboards.
"""

# %%
from __future__ import annotations

import shutil

from gemseo.algos.parameter_space import ParameterSpace

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.api import load_model_results
from vimseo.api import search_model_results
from vimseo.tools.doe.doe import DOETool

# %%
# Generate the results
# --------------------
# A DOE of a beam in bending gives a tool result, and a model result per simulation:
archive = {
    "archive_manager": "DirectoryArchive",
    "directory_archive_root": EXAMPLE_RUNS_DIR / "archive/data_management/visualize",
    "study_name": "visualize",
}
shutil.rmtree(archive["directory_archive_root"], ignore_errors=True)

model = create_model(
    "BendingTestAnalytical",
    "Cantilever",
    **archive,
    cache_file_path=archive["directory_archive_root"] / "cache.hdf",
)
parameter_space = ParameterSpace()
parameter_space.add_random_variable(
    "height", "OTUniformDistribution", minimum=30.0, maximum=60.0
)
doe = DOETool(**archive)
doe.execute(model=model, parameter_space=parameter_space, n_samples=5)

tool_result = doe.result
model_results = load_model_results(tool_result.metadata.simulation_run_ids, **archive)
model_result = model_results[0]

# %%
# Figures
# -------
# ``plot()`` returns the figures of a result, by name. Every kind of result has its own
# plot settings, passed as keyword arguments to ``plot()``; they are all optional:
# by default, every figure is drawn with every variable. ``get_plot_choices()`` gives,
# for each setting selecting names, the names it accepts.
#
# ### Figures of a model result
# A model result draws the figures declared by its model (``PLOTS``). Its only setting
# is ``plot_names``, the names of the figures to draw:
model_result.get_plot_choices()

# %%
figures = model_result.plot(plot_names=["moment_vs_moment_grid"])
figures["moment_vs_moment_grid"]

# %%
# A figure is named after its ``Plot``: its ``name`` if it is set, else its ``title``
# in lower case with underscores, else ``{y}_vs_{x}`` from its ordinate and abscissa
# names. A figure drawing several ordinates is then named after the first one,
# ``{first y}_and_{n - 1}_more_vs_{x}``, which is hard to guess: ``get_plot_choices()``
# gives it, and a ``Plot`` with several lines deserves a ``name``. The model
# ``MockMultiCurves`` declares a figure of three energies without name nor title, and
# a figure with a title:
multi_curve_model = create_model(
    "MockMultiCurves",
    "Dummy",
    **archive,
    cache_file_path=archive["directory_archive_root"] / "multi_curves_cache.hdf",
)
multi_curve_model.execute()
(summary,) = search_model_results(**archive, model_name="MockMultiCurves")
multi_curve_result = load_model_results(summary["uri"], **archive)[0]
multi_curve_result.get_plot_choices()

# %%
figures = multi_curve_result.plot()
figures["energy_strain_history_and_2_more_vs_displacement_history"]

# %%
figures["crack_propagation"]

# %%
# ### Figures of a tool result
# A tool result draws the figures of its tool, with the settings of its tool. A DOE
# result draws a scatter matrix of its scalar variables, the scalar outputs versus the
# input varying between the samples, and the curves of the model superposed over the
# samples:
figures = tool_result.plot()
list(figures)

# %%
# Its settings select the outputs, the abscissa of the parametric study and the
# variables of the scatter matrix:
tool_result.get_plot_choices()

# %%
# A parametric study is drawn for a *family* of samples, differing by the abscissa
# only. Here, ``height`` is the only varying input, so all the samples form a single
# family. When several inputs vary, as in a factorial design, there is a family per
# value of the other varying inputs: the scalar outputs are drawn with a line per
# family, or in a figure per family with ``family_layout="one_figure_per_family"``,
# and the curves in a figure per family, e.g.
# ``curves_moment_vs_moment_grid[width=20.0]``. A design varying the inputs jointly,
# like a LHS, has no family: only its scatter matrix is relevant.

# %%
figures = tool_result.plot(scatter_matrix_variable_names=["height", "reaction_forces"])
figures["scatter_matrix"]

# %%
# The figures are written to files with ``save=True``:
figures = tool_result.plot(
    save=True, directory_path=EXAMPLE_RUNS_DIR / "visualization/data_management"
)

# %%
# ### Figures of several results
# ``model_results.visualize()`` superposes the curves of the model results of a collection,
# one figure per figure of the model, the curves being labelled by the inputs varying
# between the results. A figure missing from some results, e.g. when they come from
# different models, is not drawn and a warning names it:
figures = model_results.visualize(plot_names=["moment_vs_moment_grid"])
figures["moment_vs_moment_grid"]

# %%
# Tables
# ------
# ``to_dataframes()`` returns the numerical values of a result as ``DataFrame``
# objects, by name. The tables of a tool result depend on its tool:
tables = tool_result.to_dataframes()
list(tables)

# %%
tables["dataset"]

# %%
# A model result gives its inputs, its outputs and its metadata:
tables = model_result.to_dataframes()
list(tables)

# %%
tables["outputs"]

# %%
# Dashboards
# ----------
#
# | Need | Command |
# | --- | --- |
# | Browse the model results of an archive, refined by study, model, load case, status or query, or any tool result, e.g. a validation case, or edit a parameter space (package `vimseo-dashboards`) | `dashboard_results` |
# | Browse the model results and the tool runs of an MLflow archive | `dashboard_mlflow` |
