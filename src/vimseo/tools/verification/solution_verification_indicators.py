# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import annotations

from statistics import median
from typing import TYPE_CHECKING

import numpy as np
from numpy import absolute
from scipy.optimize import curve_fit
from scipy.optimize import fsolve

if TYPE_CHECKING:
    from numpy import ndarray


def compute_median(q: ndarray, q_ref: float):
    """Estimate the extrapolated value at element size = 0.

    The uncertainty is computed from the Median Absolute Deviation (MAD).

    Args:
        q: The model output values.
        q_ref: A reference value in which we have most confidence. The final
        estimate for the extrapolated q is a weighted sum of the median and q_ref.

    Returns:
        A tuple where first element is the estimate of the extrapolated value,
        and second is the MAD.
    """
    q_median = median(q)
    w = 0.66
    q_final = q_ref * w + q_median * (1 - w)
    # Coefficient for a normal distribution:
    q_mad = 1.4826 * median(absolute(q - q_final))
    return q_final, q_mad


def compute_c(e_q_j, gamma_j_1, gamma_j, beta):
    r"""Compute constant $C$.

    Args:
        e_q_j: The error expansion ($q_{exact} - q_j$) for grid j.
        gamma_j_1: The relative element size for grid j+1.
        gamma_j: The relative element size for grid j.
        beta: The convergence order.

    Returns:
        The constant $C$.
    """
    return e_q_j / (-(gamma_j_1**beta) + gamma_j**beta)


def compute_q_extrap(j, c, q, gamma, beta):
    r"""Compute the extrapolated value at element size = 0.

    Args:
        j: The grid index.
        c: The $C$ constant.
        q: The model solution array indexed for j.
        gamma: The relative element size array indexed for j.
        beta: The convergence order.

    Returns:
        The extrapolated value of the model solution at element size = 0.
    """
    return q[j] + c * gamma[j] ** beta


def compute_richardson(h, q):
    r"""Compute Richardson extrapolation.

    Args:
        h: The array of element sizes.
        q: The array of model solutions.

    Returns:
        The Richardson extrapolation of q at element size = 0.
    """
    # Arbitrary coefficient > 1 to define a base h value $h_0$.
    h_0 = h[0] * 1.1
    # Solve equation for $\beta$:
    beta, _infos, status, _msg = fsolve(
        beta_func,
        1.0,
        args=(
            q[1] - q[0],
            q[2] - q[1],
            h[0] / h_0,
            h[1] / h_0,
            h[2] / h_0,
        ),
        full_output=True,
    )
    beta = beta[0]
    if status == 1 and beta >= 0:
        c = compute_c(q[1] - q[0], h[1] / h_0, h[0] / h_0, beta)
        q_extrap = compute_q_extrap(0, c, q, h / h_0, beta)
        return beta, q_extrap
    return np.nan, np.nan


def beta_func(beta, e_q_1, e_q_2, gamma_1, gamma_2, gamma_3):
    return e_q_1 / (-(gamma_2**beta) + gamma_1**beta) - e_q_2 / (
        -(gamma_3**beta) + gamma_2**beta
    )


def fit_power_law(
    h: ndarray, q: ndarray, order_bounds: tuple[float, float] = (0.1, 4.0)
) -> tuple[float, float, float, float]:
    r"""Least-squares power-law fit of the convergence, as a robust alternative to
    Richardson.

    The model :math:`q(h) = q_\infty + C\,h^p` is fitted over **all** grids by
    least squares, with the convergence order :math:`p` treated as a *fitted*
    parameter (it is not assumed). Compared with :func:`compute_richardson`, which
    solves an exact three-point equation and returns ``nan`` as soon as one triplet
    is not power-law convergent, this fit:

    - uses every grid, so isolated noise does not destroy the estimate;
    - never raises: if the optimisation does not converge (for instance on
      strongly non-monotone "sawtooth" data) it returns ``nan`` values instead;
    - reports a residual, which quantifies how power-law the convergence actually
      is (a large residual flags an unreliable extrapolation).

    Args:
        h: The element sizes.
        q: The model solutions for each element size.
        order_bounds: The lower and upper bounds constraining the search for the
            convergence order ``p``. These bound the optimisation only; they do not
            assume a particular order.

    Returns:
        The converged value :math:`q_\infty`, the fitted order :math:`p`, the
        coefficient :math:`C` and the RMS residual of the fit. All ``nan`` if the
        fit does not converge.
    """
    h = np.asarray(h, dtype=float)
    q = np.asarray(q, dtype=float)

    def power_law(element_size, q_converged, coefficient, order):
        return q_converged + coefficient * element_size**order

    # Initial guess: the finest-grid value as the asymptote, an order of 2, and a
    # coefficient matching the observed coarse-to-fine variation.
    q_converged_0 = float(q[np.argmin(h)])
    coefficient_0 = (float(q[np.argmax(h)]) - q_converged_0) / (h.max() ** 2.0)
    try:
        parameters, _ = curve_fit(
            power_law,
            h,
            q,
            p0=(q_converged_0, coefficient_0, 2.0),
            bounds=(
                (-np.inf, -np.inf, order_bounds[0]),
                (np.inf, np.inf, order_bounds[1]),
            ),
            maxfev=10000,
        )
    except (RuntimeError, ValueError):
        return np.nan, np.nan, np.nan, np.nan

    q_converged, coefficient, order = parameters
    rmse = float(np.sqrt(np.mean((q - power_law(h, *parameters)) ** 2)))
    return float(q_converged), float(order), float(coefficient), rmse


def robust_converged_value(q: ndarray, n_finest: int = 3) -> tuple[float, float]:
    """Model-free estimate of the converged value from the finest grids.

    The converged value is taken as the median of the ``n_finest`` finest-grid
    outputs and its uncertainty as their scaled median absolute deviation (MAD).
    This estimate assumes no convergence order at all, never fails, and is well
    suited to non-monotone ("sawtooth") convergence: the true value then lies near
    the centre of the oscillation envelope, which the median captures while the
    spread reports the residual mesh sensitivity.

    Args:
        q: The model solutions, ordered from the coarsest to the finest grid (the
            finest grids are the last entries, following the tool convention).
        n_finest: The number of finest grids used for the estimate.

    Returns:
        The converged value and its uncertainty band (``1.4826 * MAD``).
    """
    q = np.asarray(q, dtype=float)
    finest = q[-min(n_finest, len(q)) :]
    q_converged = float(np.median(finest))
    band = float(1.4826 * np.median(np.absolute(finest - q_converged)))
    return q_converged, band


def cross_validated_mad(values: ndarray) -> tuple[float, float]:
    """Median and scaled MAD of a set of cross-validation fold estimates.

    Non-finite fold estimates (e.g. folds where a palliative could not be
    computed) are ignored. Returns ``(nan, nan)`` if no finite value is left.

    Args:
        values: The per-fold estimates of a converged value.

    Returns:
        The median across folds and the associated uncertainty band
        (``1.4826 * MAD``).
    """
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return np.nan, np.nan
    center = float(np.median(finite))
    band = float(1.4826 * np.median(np.absolute(finite - center)))
    return center, band


def compute_gci(fs, h, q, beta, starting_mesh_id):
    """The Grid Convergence Index.

    Computed from the two finest meshes.

    Args:
        fs: The safety factor.
        h: The element sizes, from coarse to fine.
        q: The output value corresponding to each element size.
        beta: The convergence order.
        starting_mesh_id: The GCI is computed based on q[starting_mesh_id] and
        q[starting_mesh_id+1].

    Returns:
        A tuple where first element is the Grid Convergence Index,
        and second element is the GCI-based error band on the solution.
    """
    gci = (
        fs
        * abs((q[starting_mesh_id + 1] - q[starting_mesh_id]) / q[starting_mesh_id + 1])
        / ((h[starting_mesh_id] / h[starting_mesh_id + 1]) ** beta - 1)
    )
    return gci, [
        q[starting_mesh_id + 1] * (1 - abs(gci)),
        q[starting_mesh_id + 1] * (1 + abs(gci)),
    ]


def compute_rde(fs, h, q, q_extrap, beta, i):
    """The Relative Discretisation Index (RDE).

    Computed from the two finest meshes.

    Args:
        fs: The safety factor.
        h: The element sizes, from coarse to fine.
        q: The output value corresponding to each element size.
        beta: The convergence order.
        q_extrap: The Richardson extrapolation.
        i: The index at which RDE is computed, from fine to coarse.

    Returns:
        A tuple where first element is the RDE,
        and second element is the RDE-based error band on the solution for the finest
        grid.
    """
    q_fine_to_coarse = q[::-1]
    h_fine_to_coarse = h[::-1]
    rde = (q_fine_to_coarse[i + 1] - q_fine_to_coarse[i]) / (
        q_extrap * ((h_fine_to_coarse[i + 1] / h_fine_to_coarse[i]) ** beta - 1)
    )
    rde_band = (
        fs / ((h_fine_to_coarse[i + 1] / h_fine_to_coarse[i]) ** beta - 1)
    ) * abs((q_fine_to_coarse[i + 1] - q_fine_to_coarse[i]) / q_extrap)
    return rde, [q[i + 1] - 0.5 * rde_band, q[i + 1] + 0.5 * rde_band]
