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

import plotly.graph_objects as go
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
from vimseo.utilities.curves import Curve
from vimseo.utilities.fields import extract_line
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
result_2 = ModelResult.from_data({
    "inputs": model.get_input_data(),
    "outputs": model.get_output_data(),
})
result_2

# %%
# The scalars can be compared in a scatter matrix:
variable_names = ["young_modulus", "reaction_forces"]
df = DataFrame([
    result.get_numeric_scalars(variable_names=variable_names),
    result_2.get_numeric_scalars(variable_names=variable_names),
])
df["color"] = range(len(df))
plot = ScatterMatrix(Dataset.from_dataframe(df), classifier="color")
plot.labels = ["result", "result 2"]
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
        result_2.get_curve(("dplt_grid", "dplt")),
    ],
    labels=["result", "result 2"],
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
plot = ScatterMatrix(Dataset.from_dataframe(df), classifier="color")
plot.labels = ["data", "model result"]
fig = plot.execute(
    save=False,
    show=True,
)
fig

# %%
# Retrieve and manipulate a field
# -------------------------------
# The models above expose scalar outputs and curves. Some models also produce
# *fields* -- variables defined over a mesh -- which can be retrieved from a
# result and post-processed: probed at a point, sampled along a line, or reshaped
# onto a grid. Here we use the analytic Tan open-hole model, which computes the
# membrane stress field around a hole in a loaded composite plate.
#
# !!! note
#
#     Executing ``TanOpenHole`` requires the ``mesh`` extra
#     (``pip install "vimseo[mesh]"``): the field is read back with ``pyvista``.
field_model_name = "TanOpenHole"
field_load_case = "Tension"
field_model = create_model(
    field_model_name,
    field_load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/visualize_model_result",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/visualize_model_result",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/visualize_model_result/{field_model_name}_{field_load_case}_cache.hdf",
    ),
)
field_model.cache = None
field_output = field_model.execute()

# %%
# The field is retrieved by rebuilding a ``ModelResult`` with ``load_fields=True``.
# ``result.fields`` maps each field name to a list of ``MeshField`` objects:
field_result = ModelResult.from_data(
    {"inputs": field_model.get_input_data(), "outputs": field_output},
    model=field_model,
    load_fields=True,
)
flux_field = field_result.fields["flux"][0]
flux_field.point_variable_names

# %%
# The mesh file backing the field is kept on disk, ready to be opened in an
# external tool such as ParaView:
flux_field.path

# %%
# We read the plate geometry and the applied far-field stress from the inputs:
inputs = field_model.get_input_data()
length = float(inputs["length"][0])
width = float(inputs["width"][0])
radius = float(inputs["radius"][0])
d0 = float(inputs["d0"][0])
applied_stress = float(inputs["load"][0])

# %%
# **Whole-field view.** Before probing into it, the field can be looked at as a
# whole. ``MeshField.to_structured_grid`` reshapes one component back onto the
# grid it is defined on, returning the ``x`` and ``y`` axes and the 2-D array of
# values (``nan`` inside the blanked hole), which plots directly as a heatmap.
# The stress concentration at the hole edge and the relaxation towards the
# applied far-field stress away from it are both visible:
grid_x, grid_y, sigma_xx_grid = flux_field.to_structured_grid("sigma_xx")
fig = go.Figure(
    go.Heatmap(
        x=grid_x,
        y=grid_y,
        z=sigma_xx_grid.T,
        colorscale="Viridis",
        colorbar={"title": "sigma_xx (MPa)"},
    )
)
fig.update_layout(
    title="sigma_xx field over the plate",
    xaxis_title="x (mm)",
    yaxis_title="y (mm)",
)
# Equal aspect ratio so the hole stays circular:
fig.update_yaxes(scaleanchor="x")
fig

# %%
# **Probing.** ``MeshField.probe`` bilinearly interpolates a component at an
# arbitrary point. Walking outward from the hole along the transverse mid-section
# (``x = length / 2``), ``sigma_xx`` decays from its peak towards the applied
# stress. The field is blanked inside ``r < radius + d0``, so a point in that
# region returns ``nan``:
probe_x = 0.5 * length
blank_edge_y = 0.5 * width + radius + d0
probe_ys = [
    0.5 * width,
    blank_edge_y + 0.5,
    blank_edge_y + 2.0,
    blank_edge_y + 5.0,
    blank_edge_y + 9.0,
]
probe_values = [flux_field.probe("sigma_xx", probe_x, y) for y in probe_ys]
for y, value in zip(probe_ys, probe_values, strict=False):
    print(f"sigma_xx at (x={probe_x:.1f}, y={y:5.2f}) = {value:8.1f} MPa")

# %%
# **Line extraction.** ``extract_line`` samples the field along a segment. We cut
# the full transverse section at ``x = length / 2``. It returns the sampling
# ``coords``, the curvilinear distance ``dist`` from the first point, and one
# array per requested field; points falling in the blanked hole come back
# ``nan``:
line = extract_line(
    flux_field.path,
    point_a=(probe_x, 0.0, 0.0),
    point_b=(probe_x, width, 0.0),
    n_points=200,
    fields=["sigma_xx"],
)
line["sigma_xx"].shape

# %%
# The extracted profile, the probe points and the model's own centre-line output
# (``line_center_sigma_xx``, sampled internally over the same segment) are drawn
# together. They overlap, which confirms the three retrieval routes are
# consistent:
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=line["coords"][:, 1],
        y=line["sigma_xx"],
        mode="lines",
        name="extract_line",
    )
)
fig.add_trace(
    go.Scatter(
        x=field_output["line_center_y"],
        y=field_output["line_center_sigma_xx"],
        mode="lines",
        line={"dash": "dot"},
        name="line_center output",
    )
)
fig.add_trace(
    go.Scatter(
        x=probe_ys,
        y=probe_values,
        mode="markers",
        marker={"size": 9, "symbol": "x"},
        name="probe",
    )
)
fig.add_hline(y=applied_stress, line_dash="dash", annotation_text="applied stress")
fig.update_layout(
    title="sigma_xx across the transverse mid-section",
    xaxis_title="y (mm)",
    yaxis_title="sigma_xx (MPa)",
)
fig

# %%
# Compare a field between two designs
# ----------------------------------
# Running the same extraction on a second design turns the field into a
# quantitative comparison. We re-execute with a 0-dominated layup, wrap each
# transverse profile in a ``Curve``, and overlay them with ``superpose_curves`` (the
# same helper used for the beam curves above), which gives each line its own
# colour and legend entry. Away from the hole both profiles relax to the applied
# far-field stress (~1000 MPa); they differ around the concentration:
field_output_ud = field_model.execute({"layup": atleast_1d([0.0] * 8)})
flux_field_ud = ModelResult.from_data(
    {"inputs": field_model.get_input_data(), "outputs": field_output_ud},
    model=field_model,
    load_fields=True,
).fields["flux"][0]
line_ud = extract_line(
    flux_field_ud.path,
    point_a=(probe_x, 0.0, 0.0),
    point_b=(probe_x, width, 0.0),
    n_points=200,
    fields=["sigma_xx"],
)

quasi_iso_curve = Curve({"y": line["coords"][:, 1], "sigma_xx": line["sigma_xx"]})
ud_curve = Curve({"y": line_ud["coords"][:, 1], "sigma_xx": line_ud["sigma_xx"]})
superpose_curves(
    [quasi_iso_curve, ud_curve],
    labels=["quasi-isotropic", "0-dominated"],
)

# %%
# Figures holding several lines
# -----------------------------
# The figures of a model are declared in its ``PLOTS`` class attribute, either as a
# tuple of variable names whose first one is the abscissa, or as a ``Plot`` object
# when the lines shall be styled, drawn against a secondary ordinate axis or
# completed with horizontal reference lines.
# The ``MockMultiCurves`` model declares two such figures:
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
# three energies are declared as a ``Plot`` object without any custom style, so the
# colours are taken from the default palette. Since the axis holds several lines, it
# is labelled with the variable names and drawn in black:
multi_curve_model.execute()
multi_figs = multi_curve_model.plot_results(show=True, save=False)
multi_figs["energy_strain_history_and_2_more_vs_displacement_history"]

# %%
# When the quantities have different magnitudes, a line can be drawn against a
# secondary ordinate axis. This second figure is declared as a ``Plot`` object: the
# force keeps the left axis, the crack position moves to the right one, and a
# horizontal reference line shows the critical crack position prescribed as a model
# input.
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
multi_result_2 = ModelResult.from_data(
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
        multi_result_2.get_curve(curve_name),
    ],
    labels=["result", "result 2"],
    show=True,
    save=False,
)

# %%
# Whole figures can be superposed as well. In that case the colour identifies the
# result and the dash pattern identifies the variable, so that a given energy
# stays comparable from one result to the other:
superpose_curves(
    [multi_result.plots[0], multi_result_2.plots[0]],
    labels=["result", "result 2"],
    show=True,
    save=False,
)
