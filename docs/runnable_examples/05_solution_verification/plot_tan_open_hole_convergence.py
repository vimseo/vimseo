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
Solution verification of the analytic Tan open-hole model
=========================================================

Assess the discretization error of the :class:`TanOpenHole` model with the
``DiscretizationSolutionVerification`` tool, and compare two field-derived
quantities: one that converges smoothly and one that exhibits a *sawtooth*
behaviour for which the Richardson extrapolation cannot be computed.

The Tan model provides an *analytic* membrane stress field for a plate with a
circular hole (see the :ref:`Tan model reference <open-hole-plate-model-tan-model>`).
The field is nonetheless evaluated on a grid whose resolution is driven by the
``coarsening_factor`` input: the grid has ``n = NOMINAL_GRID_SIZE / coarsening_factor``
points per direction, so a larger ``coarsening_factor`` gives a coarser grid.

Because the solution is analytic, the values stored at the grid nodes are exact.
What a coarse grid degrades is any quantity read from the discrete field. We look
at two of them:

- ``sigma_xx_probe``: ``sigma_xx`` bilinearly interpolated at a fixed point just
  outside the hole. It converges smoothly as the grid is refined.
- ``sigma_xx_peak``: the maximum of ``sigma_xx`` over the grid nodes. Because the
  node that happens to fall closest to the stress concentration jumps around as
  the grid changes, this quantity is *non-monotone* -- a sawtooth.

The three-point Richardson extrapolation is fragile: its cross-validation returns
``nan`` as soon as one grid triplet is not cleanly power-law convergent, which
happens systematically for the sawtooth quantity but also for the smooth one on
sampled data. The tool therefore also reports two Richardson-independent estimates
of the converged value -- a least-squares power-law fit, whose order is fitted
rather than assumed, and a model-free median of the finest grids -- which stay
available in both cases. Their residual (fit) and band (median) quantify how
reliable the estimate is.
"""

# %%
from __future__ import annotations

import logging

import numpy as np
import plotly.graph_objects as go
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import atleast_1d
from pandas import DataFrame
from plotly.subplots import make_subplots
from scipy.interpolate import RegularGridInterpolator

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_result import ModelResult
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.verification.solution_verification import (
    DiscretizationSolutionVerification,
)
from vimseo.utilities.datasets import dataframe_to_dataset

# %%
# First we set the logger level:
activate_logger(level=logging.INFO)

# %%
# The model to verify is the analytic Tan open-hole model, loaded in tension:
model_name = "TanOpenHole"
load_case = "Tension"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/solution_verification",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/solution_verification",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/solution_verification/{model_name}_{load_case}_cache.hdf",
    ),
)
# The same job directory is reused across the runs of this study:
model.archive_manager._accept_overwrite_job_dir = True

# %%
# We define a set of grid coarsening factors, from coarse to fine. The tool
# requires strictly decreasing "element sizes"; here the coarsening factor plays
# that role, as it is proportional to the grid spacing.
coarsening_factors = [4.0, 3.0, 2.0, 1.5, 1.0, 0.5]


# %%
# The model writes the stress field to a VTK file. Converting the raw
# ``output_data`` into a :class:`ModelResult` exposes it as a ``Field`` through
# the ``fields`` attribute. The two helpers below reshape a nodal field back to
# the structured grid it was computed on, and sample it at an arbitrary point:
def field_to_grid(field, name):
    """Return the ``(x, y, z)`` structured grid of a nodal field component."""
    points = field.mesh_points
    n = round(len(points) ** 0.5)  # the grid is square (n x n)
    x = np.linspace(0.0, points[:, 0].max(), n)
    y = np.linspace(0.0, points[:, 1].max(), n)
    z = field.point_data[name].reshape(n, n)
    return x, y, z


def probe_field(field, name, point_x, point_y):
    """Bilinearly interpolate a nodal field component at ``(point_x, point_y)``."""
    x, y, z = field_to_grid(field, name)
    interpolator = RegularGridInterpolator(
        (x, y), z, bounds_error=False, fill_value=np.nan
    )
    return float(interpolator([[point_x, point_y]])[0])


def side_by_side(fig_left, fig_right, left_title, right_title, y_title):
    """Place the traces of two plotly figures in a single 1x2 subplot figure."""
    combined = make_subplots(rows=1, cols=2, subplot_titles=(left_title, right_title))
    for trace in fig_left.data:
        combined.add_trace(trace, row=1, col=1)
    for trace in fig_right.data:
        # Avoid duplicating the shared legend entries in the right-hand panel.
        trace.showlegend = False
        combined.add_trace(trace, row=1, col=2)
    combined.update_xaxes(title_text="coarsening_factor")
    combined.update_yaxes(title_text=y_title, row=1, col=1)
    return combined


# %%
# We run the model for each coarsening factor and collect two field-derived
# quantities: the smooth probe stress and the sawtooth peak stress.
model.execute({"coarsening_factor": atleast_1d(coarsening_factors[0])})
input_data = model.get_input_data()
length = float(input_data["length"][0])
width = float(input_data["width"][0])
radius = float(input_data["radius"][0])
probe_x = 0.5 * length
probe_y = 0.5 * width + radius + 3.0

probe_stresses = []
peak_stresses = []
model_results = {}
for coarsening_factor in coarsening_factors:
    output_data = model.execute({"coarsening_factor": atleast_1d(coarsening_factor)})
    result = ModelResult.from_data(
        {"outputs": output_data, "inputs": model.get_input_data()},
        model=model,
        load_fields=True,
    )
    field = result.fields["flux"][0]
    probe_stresses.append(probe_field(field, "sigma_xx", probe_x, probe_y))
    peak_stresses.append(float(np.nanmax(field.point_data["sigma_xx"])))
    model_results[coarsening_factor] = result

convergence_table = DataFrame({
    "coarsening_factor": coarsening_factors,
    "sigma_xx_probe": probe_stresses,
    "sigma_xx_peak": peak_stresses,
})
print(convergence_table)

# %%
# The tool consumes an ``IODataset``. We assemble it from the convergence table
# with the ``dataframe_to_dataset`` helper, using the ``name{group}`` naming
# convention to place the coarsening factor in the input group and the two
# stresses in the output group:
dataset = dataframe_to_dataset(
    convergence_table.rename(
        columns={
            "coarsening_factor": "coarsening_factor{inputs}",
            "sigma_xx_probe": "sigma_xx_probe{outputs}",
            "sigma_xx_peak": "sigma_xx_peak{outputs}",
        }
    )
)

# %%
# A smoothly converging quantity
# ------------------------------
# We first verify the smooth probe stress. It converges monotonically, so the
# power-law fit recovers the converged stress with a small residual. The
# three-point Richardson cross-validation may still return ``nan`` here: it is
# fragile as soon as one grid triplet is ill-conditioned, which is one of the
# motivations for the robust estimators.
verificator = DiscretizationSolutionVerification(
    directory_naming_method=DirectoryNamingMethod.NUMBERED,
    working_directory="DiscretizationSolutionVerification_probe",
)
verificator.execute(
    simulated_data=dataset,
    element_size_variable_name="coarsening_factor",
    abscissa_name="coarsening_factor",
    output_name="sigma_xx_probe",
)
extrapolation = verificator.result.extrapolation
print("Richardson q_extrap:", extrapolation["q_extrap"])
print(
    f"Power-law fit: q_converged={extrapolation['q_converged_fit']:.2f}, "
    f"order={extrapolation['order_fit']:.2f}, rmse={extrapolation['fit_rmse']:.2g}"
)
print(
    f"Robust median: q_converged={extrapolation['q_converged_robust']:.2f} "
    f"+/- {extrapolation['q_converged_robust_band']:.2g}"
)
# The tool selects Richardson when available and falls back to a palliative
# otherwise; ``q_converged_method`` says which one was used.
print(
    f"Selected converged value: {extrapolation['q_converged']:.2f} "
    f"(method: {extrapolation['q_converged_method']})"
)

# %%
# The convergence-fit plot shows the sampled stress, the fitted power law and the
# converged-value estimates at a null element size:
figures = verificator.plot_results(
    verificator.result,
    save=False,
    show=True,
    directory_path=verificator.working_directory,
)
figures["convergence_fit"]

# %%
# A sawtooth quantity
# -------------------
# We now verify the peak stress. Its non-monotone (sawtooth) behaviour makes the
# three-point Richardson extrapolation fail (``nan``), so the Richardson-based
# indicators are unavailable:
verificator_peak = DiscretizationSolutionVerification(
    directory_naming_method=DirectoryNamingMethod.NUMBERED,
    working_directory="DiscretizationSolutionVerification_peak",
)
verificator_peak.execute(
    simulated_data=dataset,
    element_size_variable_name="coarsening_factor",
    abscissa_name="coarsening_factor",
    output_name="sigma_xx_peak",
)
extrapolation_peak = verificator_peak.result.extrapolation
print(
    "Richardson q_extrap (nan expected for sawtooth):", extrapolation_peak["q_extrap"]
)
# The residual and band are now much larger than for the smooth probe, correctly
# flagging that this converged value is far less trustworthy.
print(
    f"Power-law fit: q_converged={extrapolation_peak['q_converged_fit']:.2f}, "
    f"order={extrapolation_peak['order_fit']:.2f}, rmse={extrapolation_peak['fit_rmse']:.2g}"
)
print(
    f"Robust median: q_converged={extrapolation_peak['q_converged_robust']:.2f} "
    f"+/- {extrapolation_peak['q_converged_robust_band']:.2g}"
)
# Richardson failed here, so the tool falls back to a palliative and says so.
print(
    f"Selected converged value: {extrapolation_peak['q_converged']:.2f} "
    f"(method: {extrapolation_peak['q_converged_method']})"
)

# %%
# Two plots are produced. The convergence-fit plot (on all grid points) stays
# informative: it overlays the power-law fit (with its fitted order and residual)
# and the model-free median of the finest grids (with its uncertainty band) on
# the sawtooth data:
figures_peak = verificator_peak.plot_results(
    verificator_peak.result,
    save=False,
    show=True,
    directory_path=verificator_peak.working_directory,
)
figures_peak["convergence_fit"]

# %%
# Discussion: smooth versus sawtooth
# ----------------------------------
# Putting the two diagnostics side by side for the two outputs tells a consistent
# story about whether the mesh is in the asymptotic (converged) regime.
#
# **Cross-validation plot** (smooth probe on the left, sawtooth peak on the right).
# For the smooth probe stress the leave-one-grid-out folds almost overlap and all
# extrapolate to nearly the same value, so the cross-validation band is tight:
# dropping any grid barely moves the estimate, a sign that the converged value is
# trustworthy. For the sawtooth peak stress the folds scatter and extrapolate to
# markedly different values, giving a wide band: the estimate depends heavily on
# which grids are used.
side_by_side(
    figures["convergence_cross_validation"],
    figures_peak["convergence_cross_validation"],
    "smooth probe (sigma_xx_probe)",
    "sawtooth peak (sigma_xx_peak)",
    "sigma_xx",
)

# %%
# **Relative-error plot** (smooth probe on the left, sawtooth peak on the right).
# For the probe the relative error with respect to the converged value decreases
# monotonically as the element size shrinks -- the expected asymptotic behaviour.
# For the peak it oscillates and does not settle, showing that the quantity never
# enters the asymptotic regime, so no meaningful discretization order (and hence
# no reliable Richardson extrapolation) exists.
side_by_side(
    figures["relative_error_versus_element_size"],
    figures_peak["relative_error_versus_element_size"],
    "smooth probe (sigma_xx_probe)",
    "sawtooth peak (sigma_xx_peak)",
    "relative error",
)

# %%
# The two diagnostics agree, and they agree with the fit residual and the robust
# band reported earlier: the probe stress is converged and its palliative value
# is reliable, whereas the peak stress is dominated by mesh sampling noise and its
# "converged value" should be treated with caution. In practice, a wide
# cross-validation band or a non-monotone relative error is the signal to refine
# the mesh further (or to pick a smoother quantity of interest) before trusting
# the extrapolation.

# %%
# Comparison of the fields
# ------------------------
# Beyond the scalar convergence, the whole ``sigma_xx`` field can be compared
# between the coarsest and the finest grid. Both are exact at their nodes, but
# the finer grid resolves the stress concentration around the hole far better:
coarse = model_results[coarsening_factors[0]].fields["flux"][0]
fine = model_results[coarsening_factors[-1]].fields["flux"][0]
x_coarse, y_coarse, z_coarse = field_to_grid(coarse, "sigma_xx")
x_fine, y_fine, z_fine = field_to_grid(fine, "sigma_xx")

color_min = float(np.nanmin([np.nanmin(z_coarse), np.nanmin(z_fine)]))
color_max = float(np.nanmax([np.nanmax(z_coarse), np.nanmax(z_fine)]))

fig = make_subplots(
    rows=1,
    cols=2,
    shared_yaxes=True,
    subplot_titles=(
        f"coarse grid (coarsening_factor={coarsening_factors[0]})",
        f"fine grid (coarsening_factor={coarsening_factors[-1]})",
    ),
)
fig.add_trace(
    go.Heatmap(
        x=x_coarse, y=y_coarse, z=z_coarse.T, coloraxis="coloraxis", name="coarse"
    ),
    row=1,
    col=1,
)
fig.add_trace(
    go.Heatmap(x=x_fine, y=y_fine, z=z_fine.T, coloraxis="coloraxis", name="fine"),
    row=1,
    col=2,
)
fig.update_layout(
    title="sigma_xx field around the hole",
    coloraxis={
        "colorscale": "Viridis",
        "cmin": color_min,
        "cmax": color_max,
        "colorbar": {"title": "sigma_xx"},
    },
)
# Equal aspect ratio so the hole stays circular in both panels:
fig.update_yaxes(scaleanchor="x", row=1, col=1)
fig.update_yaxes(scaleanchor="x2", row=1, col=2)
fig
