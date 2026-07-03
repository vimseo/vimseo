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

# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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


import numpy as np
import pytest
from numpy.testing import assert_array_almost_equal

from vimseo.api import create_model
from vimseo.core.model_result import ModelResult
from vimseo.lib_vimseo import tan_lib
from vimseo.problems.tan_oh.tan_oht import NOMINAL_GRID_SIZE
from vimseo.problems.tan_oh.tan_oht import PLY_THICKNESS
from vimseo.problems.tan_oh.tan_oht import STIFFNESS_PROPERTY_NAMES
from vimseo.problems.tan_oh.tan_oht import compute_c_strat
from vimseo.problems.tan_oh.tan_oht import material

# The default stacking is quasi-isotropic, which drives ``tan_lib`` to its two
# degeneracies: the orthotropy axes are undefined (handled by the omega = 0
# short-circuit in ``Calc_S_matrix``) and the characteristic roots merge, s1 = s2
# (handled by the root-separation floor in ``Calc_S12_eff``). Both are needed for
# this reference value to be deterministic and reproducible across BLAS/platforms.
QUASI_ISOTROPIC_STACKING = np.array([0.0, 45.0, -45.0, 90.0, 90.0, -45.0, 45.0, 0.0])

# A strongly orthotropic (0-dominant) stacking. Its roots s1 and s2 are well
# separated (|s1 - s2| ~ 4.2), so the solution is well conditioned and
# reproducible across platforms (see the module docstring of ``tan_lib``).
ORTHOTROPIC_STACKING = np.array([0.0, 0.0, 90.0, 0.0, 0.0, 90.0, 0.0, 0.0])


def _build_c_strat(stacking: np.ndarray) -> tuple[np.ndarray, float]:
    """Build the effective membrane stiffness ``c_strat`` for a stacking.

    Uses the model's ``compute_c_strat`` with the default material values.
    """
    properties = material.get_values_as_dict()
    c_strat = compute_c_strat(
        stacking, *(properties[name] for name in STIFFNESS_PROPERTY_NAMES)
    )
    total_thickness = len(stacking) * PLY_THICKNESS
    return np.array(c_strat), total_thickness


@pytest.mark.parametrize(
    ("stacking", "expected_sigma_xx_d0"),
    [
        pytest.param(QUASI_ISOTROPIC_STACKING, 2094.956, id="quasi_isotropic"),
        pytest.param(ORTHOTROPIC_STACKING, 1972.320, id="orthotropic"),
    ],
)
def test_tan_oh(tmp_wd, stacking, expected_sigma_xx_d0):
    """Run the Tension Tan model for a given laminate and check its outputs."""
    # c_strat is now derived from the stacking, so only the stacking is passed.
    model = create_model("TanOpenHole", "Tension")
    output_data = model.execute({"stacking_sequence": stacking})
    input_data = model.get_input_data()
    thickness = input_data["thickness"][0]
    model_result = ModelResult.from_data(
        {"outputs": output_data, "inputs": input_data}, load_fields=True
    )

    # N_ij fields must equal sigma_ij / thickness on the whole grid.
    for n_name, sigma_name in zip(
        ["N_xx", "N_yy", "N_xy"], ["sigma_xx", "sigma_yy", "sigma_xy"], strict=False
    ):
        n_data = model_result.fields["flux"][0].point_data[n_name]
        sigma_data = model_result.fields["flux"][0].point_data[sigma_name]
        assert n_data.shape == ((NOMINAL_GRID_SIZE * NOMINAL_GRID_SIZE),)
        assert_array_almost_equal(n_data, sigma_data / thickness)

    sigma_xx_d0 = output_data["sigma_xx_d0"][0]
    # Physical sanity: finite, positive, and above the applied far-field stress
    # (there is a stress concentration next to the hole). ``load`` is the applied
    # stress, and sigma = N * thickness, so the far-field stress is ``load``.
    applied_stress = input_data["load"][0]
    assert np.isfinite(sigma_xx_d0)
    assert sigma_xx_d0 > applied_stress
    assert sigma_xx_d0 == pytest.approx(expected_sigma_xx_d0, rel=1e-2)

    assert (model.archive_manager.job_directory / "flux.vtk").exists()


def test_tan_solution_is_continuous_through_isotropy():
    """The Tan stress must vary continuously as a laminate approaches isotropy.

    The Tan potentials divide by (s1 - s2), which vanishes at the isotropic
    double root. Without regularisation the solution loses precision below
    |s1 - s2| ~ 1e-6 and returns NaN at exactly isotropy. Here a stiffness family
    is morphed from orthotropic down to perfectly isotropic; the stress must stay
    finite and must not jump. This is a fast, lib-level check (no full model run).
    """
    c_iso = np.array([[6e10, 2e10, 0.0], [2e10, 6e10, 0.0], [0.0, 0.0, 2e10]])
    # Breaks the C11 == C22 symmetry without adding coupling.
    breaker = np.array([[1e10, 0.0, 0.0], [0.0, -1e10, 0.0], [0.0, 0.0, 0.0]])
    r, theta = 8.37, 0.9123
    load = np.array([1e6, 0.0, 0.0])
    radius, width = 3.175, 32.0

    # Anisotropy amplitudes decreasing down to perfect isotropy (0.0). This range
    # crosses both the omega = 0 short-circuit and the root-separation floor.
    alphas = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-8, 1e-10, 0.0]
    stresses = np.array([
        tan_lib.tan_model(r, theta, load, c_iso + alpha * breaker, radius, width)[0]
        for alpha in alphas
    ])

    # No division-by-zero blow-up, even at exact isotropy.
    assert np.all(np.isfinite(stresses))

    # No brutal jump: the relative change between consecutive (increasingly
    # isotropic) laminates stays small over the whole sweep.
    relative_steps = np.abs(np.diff(stresses)) / np.abs(stresses[:-1])
    assert np.max(relative_steps) < 1e-2

    # The near-isotropic tail has settled: the solution converges to a limit
    # instead of oscillating or diverging.
    tail = stresses[-4:]
    assert np.ptp(tail) < 1e-4 * np.abs(stresses[-1])


def test_tan_oh_jacobian(tmp_wd):
    """The analytic JAX Jacobian matches finite differences (gemseo check_jacobian).

    Requires the ``jax`` extra. Checked on a well-conditioned orthotropic
    laminate with non-stationary ply angles (so ``d/d(angle) != 0``), made the
    model default so gemseo's finite differences perturb around it for the
    non-differentiated inputs. ``c_strat`` is derived from the stacking and the
    ply elastic constants, so ``stacking_sequence`` and ``E1/E2/G12/nu12`` are
    genuine differentiated inputs (CLT chain). A per-input step scaled to the
    input magnitude is used because the inputs span very different scales.
    """
    pytest.importorskip("jax")

    stacking = np.array([30.0, -30.0, 60.0, 15.0, 15.0, 60.0, -30.0, 30.0])

    model = create_model("TanOpenHole", "Tension")
    model.default_input_data.update({"stacking_sequence": stacking})
    model.execute()
    model.cache = None  # force finite differences to actually re-execute

    inputs = model.get_input_data()
    checked_inputs = [
        "load",
        "radius",
        "width",
        "d0",
        "stacking_sequence",
        "E1",
        "E2",
        "G12",
        "nu12",
    ]
    for name in checked_inputs:
        # Step scaled to the input magnitude, floored so it is never 0 (e.g. when
        # the first component of an input happens to be 0).
        step = 1e-6 * max(abs(float(inputs[name].flat[0])), 1.0)
        assert model.check_jacobian(
            input_names=[name],
            output_names=["sigma_xx_r", "sigma_xx_d0"],
            step=step,
            threshold=1e-5,
        ), f"Jacobian check failed for input {name!r}"


def test_tan_oh_jacobian_near_isotropy():
    """Document the gradient-vs-FD gap of d(sigma_xx_d0) near isotropy.

    Requires the ``jax`` extra. The numpy forward and the JAX kernel are
    identical here, so this gap is not a numpy/JAX artefact: near a
    (quasi-)isotropic laminate the Tan solution has a *kink* in ``radius`` / ``d0``
    (a zeta branch flips as the evaluation point moves through the near-double
    root), so its one-sided derivatives differ. The analytic (one-sided) gradient
    then departs from a central finite difference (which averages across the
    kink) by a few percent, while ``load`` and ``width`` stay accurate. This is a
    fast, lib-level check that records the gap and guards against a blow-up (NaN
    or a wildly wrong gradient).
    """
    pytest.importorskip("jax")
    import jax
    import jax.numpy as jnp

    from vimseo.lib_vimseo import tan_lib_jax

    radius, width, d0, load_x, thickness = 3.175, 32.0, 0.71, 1000.0, 8 * PLY_THICKNESS

    def sigma_numpy(load_x, radius, width, d0, c_strat):
        load = np.array([load_x / thickness, 0.0, 0.0])
        return (
            thickness
            * tan_lib.tan_model(radius + d0, np.pi / 2, load, c_strat, radius, width)[0]
        )

    isotropic = np.array([[6e10, 2e10, 0.0], [2e10, 6e10, 0.0], [0.0, 0.0, 2e10]])
    laminates = {
        "quasi_isotropic": _build_c_strat(QUASI_ISOTROPIC_STACKING)[0],
        "isotropic": isotropic,
    }
    names = ["load", "radius", "width", "d0"]
    base = [load_x, radius, width, d0]
    # load/width stay tight; radius/d0 legitimately drift a few % near isotropy.
    bounds = {"load": 1e-4, "width": 1e-4, "radius": 0.1, "d0": 0.1}

    for c_strat in laminates.values():
        analytic = jax.grad(
            lambda lx, r, w, dd, c=c_strat: tan_lib_jax.sigma_xx_hole_edge(
                lx, r, w, dd, thickness, jnp.asarray(c)
            ),
            argnums=(0, 1, 2, 3),
        )(*base)
        for i, name in enumerate(names):
            analytic_i = float(analytic[i])
            assert np.isfinite(analytic_i)
            h = 1e-6 * abs(base[i])
            plus = list(base)
            plus[i] += h
            minus = list(base)
            minus[i] -= h
            fd = (sigma_numpy(*plus, c_strat) - sigma_numpy(*minus, c_strat)) / (2 * h)
            rel_err = abs(analytic_i - fd) / max(abs(fd), 1e-9)
            assert rel_err < bounds[name], f"{name}: rel_err={rel_err:.2e}"


def test_numpy_and_jax_forwards_match():
    """The numpy forward and the JAX kernel must evaluate the same function.

    The model forward is numpy while its Jacobian is computed by JAX, so the two
    must agree for the Jacobian to be consistent with the discipline output.

    The scalar model outputs (``sigma_xx_r``, ``sigma_xx_d0`` -- the Jacobian
    basis) are checked tightly for both a well-conditioned and a quasi-isotropic
    laminate. The full flux field is checked on the well-conditioned laminate
    only: near isotropy a few near-zero-flux points differ in sign (zeta branch
    selection at ``real(.) == 0``), negligible in absolute terms but large in
    relative terms, so a whole-field tight check there would be meaningless.
    """
    pytest.importorskip("jax")
    import jax.numpy as jnp

    from vimseo.lib_vimseo import tan_lib_jax

    length, width, radius, d0, load_x = 80.0, 32.0, 3.175, 0.71, 1000.0
    thickness = len(ORTHOTROPIC_STACKING) * PLY_THICKNESS
    load = np.array([load_x / thickness, 0.0, 0.0])

    # (a) scalar model outputs match for both laminates.
    for stacking in (ORTHOTROPIC_STACKING, QUASI_ISOTROPIC_STACKING):
        c_strat = _build_c_strat(stacking)[0]
        numpy_r = (
            thickness
            * tan_lib.tan_model(radius, np.pi / 2, load, c_strat, radius, width)[0]
        )
        numpy_d0 = (
            thickness
            * tan_lib.tan_model(radius + d0, np.pi / 2, load, c_strat, radius, width)[0]
        )
        jax_r, jax_d0 = np.asarray(
            tan_lib_jax.scalar_outputs(
                load_x, radius, width, d0, thickness, jnp.asarray(c_strat)
            )
        )
        assert numpy_r == pytest.approx(jax_r, rel=1e-6)
        assert numpy_d0 == pytest.approx(jax_d0, rel=1e-6)

    # (b) whole flux field matches on the well-conditioned orthotropic laminate.
    c_strat = _build_c_strat(ORTHOTROPIC_STACKING)[0]
    x = np.linspace(0, length, NOMINAL_GRID_SIZE)
    y = np.linspace(0, width, NOMINAL_GRID_SIZE)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    r = np.sqrt((xx - 0.5 * length) ** 2 + (yy - 0.5 * width) ** 2).ravel()
    theta = np.arctan2(yy - 0.5 * width, xx - 0.5 * length).ravel()
    outside = r >= radius
    numpy_flux = tan_lib.tan_model_grid(
        r[outside], theta[outside], load, c_strat, radius, width
    )
    jax_flux = np.asarray(
        tan_lib_jax.tan_point(
            jnp.asarray(r[outside]),
            jnp.asarray(theta[outside]),
            jnp.asarray(load),
            jnp.asarray(c_strat),
            radius,
            width,
        )
    ).T
    np.testing.assert_allclose(jax_flux, numpy_flux, rtol=1e-8, atol=1e-6)
