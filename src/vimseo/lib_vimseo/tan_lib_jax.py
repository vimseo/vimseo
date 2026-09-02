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

"""Differentiable JAX port of the Tan open-hole kernel (:mod:`tan_lib`).

This is an *optional* module: it requires JAX (``pip install vimseo[jax]``) and
exists to obtain gradients of the model outputs with respect to the inputs via
:func:`jax.grad` / :func:`jax.jacobian`. The forward result matches
:mod:`tan_lib` to rounding.

Differentiability notes
-----------------------
The numerical-stability logic of :mod:`tan_lib` (the isotropy short-circuit in
``Calc_S_matrix`` and the root-separation floor in ``Calc_S12_eff``) relies on
data-dependent branches around quantities that vanish at isotropy. Two things
must be handled for autodiff:

1. **Data-dependent ``if`` -> ``jnp.where``.** JAX cannot trace Python branches
   on traced values, so every branch is expressed with ``jnp.where``.

2. **The ``jnp.where`` singular-branch trap.** ``jnp.where`` evaluates *both*
   branches; if the non-selected branch divides by (or takes the ``sqrt`` of) a
   quantity that is zero exactly where that branch is *not* taken, the forward
   value is still correct but the reverse-mode gradient is ``nan`` (it flows
   through the dead branch). Every such branch below feeds a *sanitised* operand
   (``_safe_denominator`` / ``jnp.abs`` under the ``sqrt``) so no ``nan``
   gradient is produced.

Intrinsic (unavoidable) non-smoothness remains at the isotropic point itself:
``S_12`` contains ``sqrt(|gamma0 - beta0|)`` whose derivative ~ ``1/sqrt(.)``
diverges as the laminate approaches isotropy (the double root). The
root-separation floor caps the *downstream* amplification but the roots' own
sensitivity is genuinely singular there; gradients very close to isotropy should
be read with that caveat.
"""

from __future__ import annotations

import jax
import jax.numpy as jnp

# The Tan numerics are ill-conditioned in float32; force double precision.
jax.config.update("jax_enable_x64", True)

# Kept identical to the numpy implementation.
_ISOTROPY_RTOL = 1e-9
_MIN_ROOT_SEPARATION = 1e-4

# Below this |gamma0 - beta0| the roots are treated as a double root for the
# gradient only: the forward value is unchanged but the singular 1/sqrt
# derivative is replaced by 0 (regularised) instead of NaN. Chosen well below
# any physical anisotropy so real laminates keep their true gradient.
_ROOT_GRAD_FLOOR = 1e-12


def _safe_denominator(value, threshold):
    """Replace ``value`` by 1 where ``|value| <= threshold``.

    Used before a division that sits in the *non-selected* branch of a
    ``jnp.where`` so the dead branch cannot emit a ``nan`` gradient.
    """
    return jnp.where(jnp.abs(value) > threshold, value, 1.0)


def principal_stress(load: jnp.ndarray) -> jnp.ndarray:
    """Angle of the principal stress directions (smooth form).

    ``0.5 * arctan2(2 N_xy, N_xx - N_yy)`` is the differentiable equivalent of
    the branch used in :mod:`tan_lib` (it handles ``N_xx == N_yy`` continuously).
    """
    return 0.5 * jnp.arctan2(2 * load[2], load[0] - load[1])


def mat_rot(angle: jnp.ndarray) -> jnp.ndarray:
    """Rotation matrix for a given angle.

    Note: the ``np.round(., 10)`` of :mod:`tan_lib` is dropped here -- rounding
    has (almost everywhere) a zero gradient and would break differentiability;
    it was only a cosmetic clean-up of ~1e-10 noise.
    """
    s = jnp.sin(angle)
    c = jnp.cos(angle)
    return jnp.array([
        [c**2, s**2, 2 * c * s],
        [s**2, c**2, -2 * c * s],
        [-c * s, c * s, c**2 - s**2],
    ])


def calc_s_matrix(c_strat: jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray]:
    """Effective compliance matrix and orthotropy angle (differentiable)."""
    scale = jnp.linalg.norm(c_strat)

    coupling = jnp.abs(c_strat[0, 2]) + jnp.abs(c_strat[1, 2])
    asymmetry = jnp.abs(c_strat[0, 0] - c_strat[1, 1])
    is_isotropic = (coupling <= _ISOTROPY_RTOL * scale) & (
        asymmetry <= _ISOTROPY_RTOL * scale
    )

    # --- omega1 (safe division to protect the dead where-branch) ---
    den1 = c_strat[0, 0] - c_strat[1, 1]
    omega1 = jnp.where(
        jnp.abs(den1) > 1e-9,
        jnp.arctan(2 * (c_strat[0, 2] + c_strat[1, 2]) / _safe_denominator(den1, 1e-9))
        / 2,
        jnp.pi / 4,
    )

    # --- omega2 (idem) ---
    den2 = jnp.abs(
        c_strat[0, 0] + c_strat[1, 1] - 2 * c_strat[0, 1] - 4 * c_strat[2, 2]
    )
    omega2 = jnp.where(
        den2 > 1e-9,
        jnp.arctan(4 * (c_strat[0, 2] + c_strat[1, 2]) / _safe_denominator(den2, 1e-9))
        / 4,
        jnp.pi / 8,
    )

    t1 = mat_rot(omega1)
    t2 = mat_rot(omega2)
    c_try1 = t1 @ c_strat @ t1.T
    c_try2 = t2 @ c_strat @ t2.T

    sum1 = jnp.abs(c_try1[-1, 0]) + jnp.abs(c_try1[-1, 1])
    sum2 = jnp.abs(c_try2[-1, 0]) + jnp.abs(c_try2[-1, 1])
    pick_2 = sum1 > sum2

    c_final = jnp.where(pick_2, c_try2, c_try1)
    omega = jnp.where(pick_2, omega2, omega1)

    # Zero the coupling row/column.
    c_final = c_final.at[-1, :2].set(0.0).at[:2, -1].set(0.0)

    # Isotropic short-circuit: undefined frame -> deterministic omega = 0.
    c_iso = c_strat.at[-1, :2].set(0.0).at[:2, -1].set(0.0)
    c_final = jnp.where(is_isotropic, c_iso, c_final)
    omega = jnp.where(is_isotropic, 0.0, omega)

    return jnp.linalg.inv(c_final), omega


def s_12(s_strat: jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray]:
    """Roots of the characteristic equation (differentiable).

    ``sqrt(|gamma0 - beta0|)`` is used in *both* branches so the dead branch
    never takes ``sqrt`` of a negative number (which would give a ``nan``
    gradient). The remaining ``1/sqrt`` singularity at ``gamma0 == beta0``
    (isotropy) is intrinsic.
    """
    gamma0 = jnp.sqrt(s_strat[1, 1] / s_strat[0, 0])
    beta0 = (2 * s_strat[0, 1] + s_strat[2, 2]) / (2 * s_strat[0, 0])

    # ``sqrt(|gamma0 - beta0|)`` has a 1/sqrt derivative that diverges to NaN at
    # the isotropic double root. Double-``where`` guard: keep the exact forward
    # value (0 at the double root) but route the gradient through a constant
    # there so it stays finite (regularised) instead of NaN.
    abs_diff = jnp.abs(gamma0 - beta0)
    tiny = abs_diff < _ROOT_GRAD_FLOOR
    safe_diff = jnp.where(tiny, 1.0, abs_diff)
    half_diff = jnp.where(tiny, 0.0, jnp.sqrt(safe_diff / 2))
    half_sum = jnp.sqrt((gamma0 + beta0) / 2)

    greater = gamma0 > beta0
    s1 = jnp.where(greater, half_diff + 1j * half_sum, 1j * (half_diff + half_sum))
    s2 = jnp.where(greater, -half_diff + 1j * half_sum, 1j * (-half_diff + half_sum))
    return s1, s2


def _separate_roots(
    s1: jnp.ndarray, s2: jnp.ndarray, min_separation: float = _MIN_ROOT_SEPARATION
) -> tuple[jnp.ndarray, jnp.ndarray]:
    """Floor the root separation (differentiable, safe direction)."""
    separation = s1 - s2
    magnitude = jnp.abs(separation)

    # Safe direction so the dead branch cannot divide by zero.
    direction = jnp.where(
        magnitude > 0, separation / jnp.where(magnitude > 0, magnitude, 1.0), 1j
    )
    midpoint = 0.5 * (s1 + s2)
    half = 0.5 * min_separation * direction

    far = magnitude >= min_separation
    return jnp.where(far, s1, midpoint + half), jnp.where(far, s2, midpoint - half)


def calc_s12_eff(c_strat: jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray]:
    """Effective ``s1``/``s2`` for a stiffness matrix (differentiable)."""
    s_strat_omega, omega = calc_s_matrix(c_strat)
    s1_st, s2_st = s_12(s_strat_omega)

    cos = jnp.cos(omega)
    sin = jnp.sin(omega)
    s1 = (s1_st * cos + sin) / (cos - s1_st * sin)
    s2 = (s2_st * cos + sin) / (cos - s2_st * sin)
    return _separate_roots(s1, s2)


def zeta(z1, z2, s1, s2, radius):
    """Zeta values; sign selection via ``jnp.where`` (differentiable)."""
    val1 = z1 / jnp.sqrt(z1**2 - radius**2 * (1 + s1**2))
    val2 = z2 / jnp.sqrt(z2**2 - radius**2 * (1 + s2**2))
    val1 = jnp.where(jnp.real(val1) >= 0, val1, -val1)
    val2 = jnp.where(jnp.real(val2) >= 0, val2, -val2)
    return val1, val2


def tan_point(
    r: jnp.ndarray,
    theta: jnp.ndarray,
    load: jnp.ndarray,
    c_strat: jnp.ndarray,
    radius: jnp.ndarray,
    width: jnp.ndarray,
) -> jnp.ndarray:
    """Differentiable equivalent of :func:`tan_lib.tan_model`.

    Returns the stress ``(N_xx, N_yy, N_xy)`` at a single point. ``r`` and
    ``theta`` may be scalars or arrays (broadcast).
    """
    a = principal_stress(load)
    m_rot = mat_rot(a)

    p = m_rot @ load
    p = p.at[2].set(0.0)

    c_pli = m_rot @ c_strat @ m_rot.T
    s1, s2 = calc_s12_eff(c_pli)

    u = 2 * radius / width
    coeff = (2 + (1 - u) ** 3) / (3 - 3 * u)

    x = r * jnp.cos(theta - a)
    y = r * jnp.sin(theta - a)
    z1 = x + s1 * y
    z2 = x + s2 * y
    zeta1, zeta2 = zeta(z1, z2, s1, s2, radius)

    denom1 = 2 * (s1 - s2) * (1 + s1 * 1j)
    denom2 = 2 * (s1 - s2) * (1 + s2 * 1j)
    phi1_0 = -1j * p[0] * (1 - zeta1) / denom1
    phi1_1 = p[1] * s2 * (1 - zeta1) / denom1
    phi2_0 = 1j * p[0] * (1 - zeta2) / denom2
    phi2_1 = -p[1] * s1 * (1 - zeta2) / denom2

    f0 = (
        p[0]
        + 2 * jnp.real(s1**2 * phi1_0 + s2**2 * phi2_0)
        + 2 * jnp.real(s1**2 * phi1_1 + s2**2 * phi2_1)
    )
    f1 = (
        2 * jnp.real(phi1_0 + phi2_0)
        + p[1]
        + 2 * jnp.real(phi1_1 + phi2_1)
    )
    f2 = (
        -2 * jnp.real(s1 * phi1_0 + s2 * phi2_0)
        - 2 * jnp.real(s1 * phi1_1 + s2 * phi2_1)
    )
    flux = jnp.stack([f0, f1, f2])

    return coeff * jnp.linalg.solve(m_rot, flux)


def scalar_outputs(
    load_x: jnp.ndarray,
    radius: jnp.ndarray,
    width: jnp.ndarray,
    d0: jnp.ndarray,
    thickness: jnp.ndarray,
    c_strat: jnp.ndarray,
) -> jnp.ndarray:
    """Scalar model outputs ``[sigma_xx_r, sigma_xx_d0]`` (differentiable).

    ``sigma_xx`` evaluated directly on the Tan solution at the hole edge
    (``r = radius``) and one characteristic distance past it
    (``r = radius + d0``), both on the transverse center line
    (``theta = pi/2``). Matches ``PostFieldExtraction`` and is the basis of
    ``TanOpenHole._compute_jacobian``. Suitable for ``jax.jacobian`` with
    respect to any input.
    """
    load = jnp.array([load_x / thickness, 0.0, 0.0])
    n_r = tan_point(radius, jnp.pi / 2, load, c_strat, radius, width)[0]
    n_d0 = tan_point(radius + d0, jnp.pi / 2, load, c_strat, radius, width)[0]
    return thickness * jnp.stack([n_r, n_d0])


def sigma_xx_hole_edge(
    load_x: jnp.ndarray,
    radius: jnp.ndarray,
    width: jnp.ndarray,
    d0: jnp.ndarray,
    thickness: jnp.ndarray,
    c_strat: jnp.ndarray,
) -> jnp.ndarray:
    """Scalar model output ``sigma_xx_d0`` (see :func:`scalar_outputs`)."""
    return scalar_outputs(load_x, radius, width, d0, thickness, c_strat)[1]


# --------------------------------------------------------------------------- #
# Classical Lamination Theory: (ply angles, material) -> c_strat.
# Differentiable port of composipy's LaminateProperty(...).A / total_thickness,
# so that sigma_xx can be differentiated w.r.t. the ply angles and the material
# elastic constants (E1, E2, G12, nu12) by the chain rule.
# --------------------------------------------------------------------------- #
def ply_stiffness(e1, e2, g12, v12) -> jnp.ndarray:
    """Reduced ply stiffness ``Q`` in the material axes (matches composipy)."""
    v21 = v12 * e2 / e1
    denominator = 1.0 - v12 * v21
    return jnp.array([
        [e1 / denominator, v12 * e2 / denominator, 0.0],
        [v12 * e2 / denominator, e2 / denominator, 0.0],
        [0.0, 0.0, g12],
    ])


def _rotated_ply_stiffness(angle_deg, q0) -> jnp.ndarray:
    """Ply stiffness rotated to the laminate axes (composipy convention)."""
    angle = angle_deg * jnp.pi / 180.0
    c = jnp.cos(angle)
    s = jnp.sin(angle)
    t_real = jnp.array([
        [c**2, s**2, 2 * c * s],
        [s**2, c**2, -2 * c * s],
        [-c * s, c * s, c**2 - s**2],
    ])
    t_engineering = jnp.array([
        [c**2, s**2, c * s],
        [s**2, c**2, -c * s],
        [-2 * c * s, 2 * c * s, c**2 - s**2],
    ])
    return jnp.linalg.inv(t_real) @ q0 @ t_engineering


def c_strat_from_layup(angles_deg, e1, e2, g12, v12) -> jnp.ndarray:
    """Effective membrane stiffness ``c_strat`` from ply angles and material.

    Equivalent to composipy's ``LaminateProperty(angles, ply).A /
    total_thickness`` for a uniform ply thickness: ``c_strat`` is then the
    average of the rotated ply stiffnesses (the ply thickness cancels out).

    Args:
        angles_deg: Ply angles in degrees, shape ``(n_plies,)``.
        e1, e2, g12, v12: Orthotropic ply elastic constants.
    """
    q0 = ply_stiffness(e1, e2, g12, v12)
    rotated = jax.vmap(lambda angle: _rotated_ply_stiffness(angle, q0))(angles_deg)
    return jnp.mean(rotated, axis=0)


def scalar_outputs_from_layup(
    load_x, radius, width, d0, angles_deg, e1, e2, g12, v12
) -> jnp.ndarray:
    """``[sigma_xx_r, sigma_xx_d0]`` as a function of ply angles and material.

    Composes the CLT map with :func:`scalar_outputs`. ``sigma_xx`` does not
    depend on the (ply) thickness, so it is not an argument. Differentiate this
    with :func:`jax.jacobian` w.r.t. ``angles_deg`` (stacking sensitivity) or
    ``e1, e2, g12, v12`` (material sensitivity).
    """
    c_strat = c_strat_from_layup(angles_deg, e1, e2, g12, v12)
    return scalar_outputs(load_x, radius, width, d0, 1.0, c_strat)
