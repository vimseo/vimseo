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
``DiscretizationSolutionVerification`` tool, which is based on the
[Richardson extrapolation](../../../reference/vimseo/tools/verification/solution_verification.md#richardson-extrapolation)
[@richardson1911_finite_differences]
[@krysl2022_confidence_intervals_richardson], and compare two
field-derived quantities: one that converges smoothly (``sigma_xx_probe``) and one that exhibits a
*sawtooth* behaviour (``sigma_xx_peak``) for which the Richardson extrapolation cannot
be computed:

- ``sigma_xx_probe``: ``sigma_xx`` bilinearly interpolated at a fixed point just
  outside the hole. It converges smoothly as the grid is refined.
- ``sigma_xx_peak``: the maximum of ``sigma_xx`` over the grid nodes. Because the
  node that happens to fall closest to the stress concentration jumps around as
  the grid changes, this quantity is *non-monotone* -- a sawtooth.

Other relevant metrics may also be integrated similarly in a minimal way.
Because the solution is analytic, the values stored at the grid nodes are exact.
What a coarse grid degrades is any quantity read from the discrete field. We look
at two of them, plus the model's own native scalar outputs as a baseline:

This model is used a use-case case, despite having a working principle different from
what is usually prone to solution verification.
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

# %%
# We define a set of grid sizes (points per direction), from coarse to fine:
grid_sizes = [25, 33, 50, 66, 100, 200]


# %%
# Helper function to place two plotly figures side by side in a single figure.
def side_by_side(fig_left, fig_right, left_title, right_title, y_title):
    """Place the traces of two plotly figures in a single 1x2 subplot figure."""
    combined = make_subplots(rows=1, cols=2, subplot_titles=(left_title, right_title))
    for trace in fig_left.data:
        combined.add_trace(trace, row=1, col=1)
    for trace in fig_right.data:
        # Avoid duplicating the shared legend entries in the right-hand panel.
        trace.showlegend = False
        combined.add_trace(trace, row=1, col=2)
    combined.update_xaxes(title_text="dx")
    combined.update_yaxes(title_text=y_title, row=1, col=1)
    return combined


# %%
# None of the four quantities of interest -- the two field-derived ones and the
# two native hole-edge stresses -- are read from a discrete field independently
# of the others, so a single loop over the grid sizes collects all of them at
# once, together with ``dx``, the physical element size used as the
# verification abscissa:
model.execute({"grid_size": atleast_1d(grid_sizes[0])})
input_data = model.get_input_data()
length = float(input_data["length"][0])
width = float(input_data["width"][0])
radius = float(input_data["radius"][0])
probe_x = 0.5 * length
probe_y = 0.5 * width + radius + 3.0

dx_values = []
probe_stresses = []
peak_stresses = []
sigma_xx_r_values = []
sigma_xx_d0_values = []
model_results = {}
for grid_size in grid_sizes:
    output_data = model.execute({"grid_size": atleast_1d(grid_size)})
    result = ModelResult.from_data(
        {"outputs": output_data, "inputs": model.get_input_data()},
        model=model,
        load_fields=True,
    )
    field = result.fields["flux"][0]
    dx_values.append(float(output_data["dx"][0]))
    probe_stresses.append(field.probe("sigma_xx", probe_x, probe_y))
    peak_stresses.append(float(np.nanmax(field.point_data["sigma_xx"])))
    sigma_xx_r_values.append(float(output_data["sigma_xx_r"][0]))
    sigma_xx_d0_values.append(float(output_data["sigma_xx_d0"][0]))
    model_results[grid_size] = result

convergence_table = DataFrame({
    "dx": dx_values,
    "sigma_xx_probe": probe_stresses,
    "sigma_xx_peak": peak_stresses,
    "sigma_xx_r": sigma_xx_r_values,
    "sigma_xx_d0": sigma_xx_d0_values,
})
print(convergence_table)

# %%
# The tool consumes an ``IODataset``. We assemble it from the convergence table
# with the ``dataframe_to_dataset`` helper, using the ``name{group}`` naming
# convention to place ``dx`` in the input group and the four stresses in the
# output group:
dataset = dataframe_to_dataset(
    convergence_table.rename(
        columns={
            "dx": "dx{inputs}",
            "sigma_xx_probe": "sigma_xx_probe{outputs}",
            "sigma_xx_peak": "sigma_xx_peak{outputs}",
            "sigma_xx_r": "sigma_xx_r{outputs}",
            "sigma_xx_d0": "sigma_xx_d0{outputs}",
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
    element_size_variable_name="dx",
    abscissa_name="dx",
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
    element_size_variable_name="dx",
    abscissa_name="dx",
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
# Native analytic outputs: a mesh-independent baseline
# ----------------------------------------------------
# The model's native scalar outputs ``sigma_xx_r`` and ``sigma_xx_d0`` are the
# hole-edge stresses evaluated directly on the analytic Tan solution (at the hole
# radius, and one stress-point distance ``d0`` beyond it). They do not read the
# discretised field at all, so they are *exactly* mesh-independent. They were
# collected in the same loop as the field-derived quantities above, so no extra
# model runs are needed here -- we just verify them from the same dataset.
# Verifying them is a useful sanity check and a third reference behaviour, next to
# the smooth and sawtooth field quantities.
native_verificators = {}
for native_output in ("sigma_xx_r", "sigma_xx_d0"):
    verificator_native = DiscretizationSolutionVerification(
        directory_naming_method=DirectoryNamingMethod.NUMBERED,
        working_directory=f"DiscretizationSolutionVerification_{native_output}",
    )
    verificator_native.execute(
        simulated_data=dataset,
        element_size_variable_name="dx",
        abscissa_name="dx",
        output_name=native_output,
    )
    native_verificators[native_output] = verificator_native
    native_extrapolation = verificator_native.result.extrapolation
    print(
        f"{native_output}: converged={native_extrapolation['q_converged']:.4f} "
        f"(method: {native_extrapolation['q_converged_method']})"
    )

# %%
# Because the values are constant, Richardson succeeds trivially and returns the
# constant as the converged value (no palliative needed). The convergence-fit
# plots are flat, side by side (``sigma_xx_r`` on the left, ``sigma_xx_d0`` on the
# right):
native_figures = {
    name: verificator.plot_results(
        verificator.result,
        save=False,
        show=True,
        directory_path=verificator.working_directory,
    )
    for name, verificator in native_verificators.items()
}
side_by_side(
    native_figures["sigma_xx_r"]["convergence_fit"],
    native_figures["sigma_xx_d0"]["convergence_fit"],
    "sigma_xx_r (hole edge)",
    "sigma_xx_d0 (stress point)",
    "sigma_xx",
)

# %%
# The relative-error plots sit at zero: these outputs carry no discretization
# error, in contrast with the field-sampled quantities above. This is exactly the
# behaviour expected of an analytical model output, and a reassuring baseline for
# the solution-verification workflow.
side_by_side(
    native_figures["sigma_xx_r"]["relative_error_versus_element_size"],
    native_figures["sigma_xx_d0"]["relative_error_versus_element_size"],
    "sigma_xx_r (hole edge)",
    "sigma_xx_d0 (stress point)",
    "relative error",
)

# %%
# Comparison of the fields
# ------------------------
# Beyond the scalar convergence, the whole ``sigma_xx`` field can be compared
# between the coarsest and the finest grid. Both are exact at their nodes, but
# the finer grid resolves the stress concentration around the hole far better:
coarse = model_results[grid_sizes[0]].fields["flux"][0]
fine = model_results[grid_sizes[-1]].fields["flux"][0]
x_coarse, y_coarse, z_coarse = coarse.to_structured_grid("sigma_xx")
x_fine, y_fine, z_fine = fine.to_structured_grid("sigma_xx")

color_min = float(np.nanmin([np.nanmin(z_coarse), np.nanmin(z_fine)]))
color_max = float(np.nanmax([np.nanmax(z_coarse), np.nanmax(z_fine)]))

fig = make_subplots(
    rows=1,
    cols=2,
    shared_yaxes=True,
    subplot_titles=(
        f"coarse grid (grid_size={grid_sizes[0]})",
        f"fine grid (grid_size={grid_sizes[-1]})",
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
