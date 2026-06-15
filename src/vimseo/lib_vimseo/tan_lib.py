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


def principal_stress(N: np.ndarray) -> float:
    """Return the angle of the principal stress directions."""

    if N[0] == N[1]:
        a1 = np.pi / 4 * (N[2] > 0) - np.pi / 4 * (N[2] < 0)

    else:
        a1 = 1 / 2 * np.arctan(2 * N[2] / (N[0] - N[1]))

    return a1


def Mat_rot(angle: float) -> np.ndarray:
    """Return the rotation matrix for a given angle."""

    s = np.sin(angle)

    c = np.cos(angle)

    return np.round(
        np.array([
            [c**2, s**2, 2 * c * s],
            [s**2, c**2, -2 * c * s],
            [-c * s, c * s, c**2 - s**2],
        ]),
        10,
    )


def force_fluxes(
    R: float,
    s1: complex,
    s2: complex,
    p: np.ndarray,
    x: float,
    y: float,
) -> np.ndarray:
    """Return the force fluxes at a given point."""

    Phi_12 = phi(x, y, p, s1, s2, R)  # tuple de (phi1,phi2)

    N_I = np.zeros(3)

    N_II = np.zeros(3)

    N_I[0] = p[0] + 2 * np.real(s1**2 * Phi_12[0][0] + s2**2 * Phi_12[1][0])

    N_I[1] = 2 * np.real(Phi_12[0][0] + Phi_12[1][0])

    N_I[2] = -2 * np.real(s1 * Phi_12[0][0] + s2 * Phi_12[1][0])

    N_II[0] = 2 * np.real(s1**2 * Phi_12[0][1] + s2**2 * Phi_12[1][1])

    N_II[1] = p[1] + 2 * np.real(Phi_12[0][1] + Phi_12[1][1])

    N_II[2] = -2 * np.real(s1 * Phi_12[0][1] + s2 * Phi_12[1][1])

    return np.vstack((N_I, N_II))


def Calc_S_matrix(C_strat: np.ndarray) -> list[np.ndarray, float]:
    """Return the effective compliance matrix and the angle of the orthotropic axes."""

    # Identification of possible reference points

    if np.abs(C_strat[0, 0] - C_strat[1, 1]) > 1e-9:
        frac = 2 * (C_strat[0, 2] + C_strat[1, 2]) / (C_strat[0, 0] - C_strat[1, 1])

        omega1 = np.arctan(frac) / 2

    else:
        omega1 = np.pi / 4

    denom = np.abs(
        C_strat[0, 0] + C_strat[1, 1] - 2 * C_strat[0, 1] - 4 * C_strat[2, 2]
    )

    if denom > 1e-9:
        frac_bis = 4 * (C_strat[0, 2] + C_strat[1, 2]) / denom

        omega2 = np.arctan(frac_bis) / 4

    else:
        omega2 = np.pi / 8

    # Possible rotation matrices

    T_omega_inv1 = Mat_rot(omega1)

    T_omega_inv2 = Mat_rot(omega2)

    # stiffness matrices in rotated coordinate systems

    C_try1 = np.linalg.multi_dot([T_omega_inv1, C_strat, T_omega_inv1.T])

    C_try2 = np.linalg.multi_dot([T_omega_inv2, C_strat, T_omega_inv2.T])

    if np.sum(np.abs(C_try1[-1, :2])) > np.sum(np.abs(C_try2[-1, :2])):
        # on cherche le repère d orthotropie avec les couplages les moins forts

        C_final = C_try2

        omega = omega2

    else:
        C_final = C_try1

        omega = omega1

    # Clean-up numerical errors

    C_final[-1, :2] = np.zeros(2)

    C_final[:2, -1] = np.zeros(2)

    return np.linalg.inv(C_final), omega


def S_12(S_strat: np.ndarray) -> tuple[complex, complex]:
    """Return the two roots of the characteristic equation."""

    gamma0 = np.sqrt(S_strat[1, 1] / S_strat[0, 0])

    beta0 = (2 * S_strat[0, 1] + S_strat[2, 2]) / (2 * S_strat[0, 0])

    if gamma0 > beta0:
        s1 = np.sqrt((gamma0 - beta0) / 2) + 1j * np.sqrt((gamma0 + beta0) / 2)

        s2 = -np.sqrt((gamma0 - beta0) / 2) + 1j * np.sqrt((gamma0 + beta0) / 2)

        return s1, s2

    s1 = 1j * (np.sqrt((beta0 - gamma0) / 2) + np.sqrt((gamma0 + beta0) / 2))

    s2 = 1j * (-np.sqrt((beta0 - gamma0) / 2) + np.sqrt((gamma0 + beta0) / 2))

    return s1, s2


def Calc_S12_eff(C_strat: np.ndarray) -> tuple[complex, complex]:
    """Return the effective s1 and s2 for a given stiffness matrix."""

    # Determination of the appropriate flexibility matrix

    S_strat_omega, omega = Calc_S_matrix(C_strat)

    # Solving characteristic equation

    s1_st, s2_st = S_12(S_strat_omega)

    s1 = (s1_st * np.cos(omega) + np.sin(omega)) / (
        np.cos(omega) - s1_st * np.sin(omega)
    )

    s2 = (s2_st * np.cos(omega) + np.sin(omega)) / (
        np.cos(omega) - s2_st * np.sin(omega)
    )

    return s1, s2


def zeta(
    z1: complex, z2: complex, s1: complex, s2: complex, R: float
) -> tuple[complex, complex]:
    """Return the zeta values for given z1, z2, s1, s2 and R."""

    val1 = z1 / np.sqrt(z1**2 - R**2 * (1 + s1**2))

    val2 = z2 / np.sqrt(z2**2 - R**2 * (1 + s2**2))

    if np.real(val1) >= 0 and np.real(val2) >= 0:
        return val1, val2

    if np.real(val1) < 0 and np.real(val2) >= 0:
        return -val1, val2

    if np.real(val1) >= 0 and np.real(val2) < 0:
        return val1, -val2

    return -val1, -val2


def phi(
    x: float, y: float, p: np.ndarray, s1: complex, s2: complex, R: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return the phi1 and phi2 values for given x, y, p, s1, s2 and R."""

    phi1 = np.zeros(2, dtype=complex)

    phi2 = np.zeros(2, dtype=complex)

    z1 = x + s1 * y

    z2 = x + s2 * y

    zeta_ = zeta(z1, z2, s1, s2, R)

    phi1[0] = -1j * p[0] * (1 - zeta_[0]) / (2 * (s1 - s2) * (1 + s1 * 1j))

    phi1[1] = p[1] * s2 * (1 - zeta_[0]) / (2 * (s1 - s2) * (1 + s1 * 1j))

    phi2[0] = 1j * p[0] * (1 - zeta_[1]) / (2 * (s1 - s2) * (1 + s2 * 1j))

    phi2[1] = -p[1] * s1 * (1 - zeta_[1]) / (2 * (s1 - s2) * (1 + s2 * 1j))

    return phi1, phi2


def tan_model(
    r: float, theta: float, N: np.ndarray, C_strat: np.ndarray, R: float, w: float
) -> np.ndarray:
    """Return the stress at a given point for a given set of parameters.
    
    Args:
        r: The distance from the hole center to the point where the stress is calculated.
        theta: The angle between the x-axis and the line connecting the hole center to the point where the stress is calculated.
        N: The applied load vector (N_x, N_y, N_xy).
        C_strat: The stiffness matrix of the laminate.
        R: The radius of the hole.
        w: The width of the plate.
    """
    # angle of the principal axis
    a = principal_stress(N)  

    M_rot = Mat_rot(a)

    # stress in the principal frame
    p = np.dot(M_rot, N)  

    p[2] = 0

    x = r * np.cos(theta - a)

    y = r * np.sin(theta - a)

    # stiffness in the principal frame
    C_pli = np.linalg.multi_dot([
        M_rot,
        C_strat,
        M_rot.T,
    ])  

    s1, s2 = Calc_S12_eff(C_pli)  

    # Infinite force fluxes along direction 1 and 2
    F_ = force_fluxes(R, s1, s2, p, x, y)  

    u = 2 * R / w

    # Correction for a finite plate
    coeff = (2 + (1 - u) ** 3) / (3 - 3 * u)  

    return coeff * np.linalg.solve(M_rot, np.sum(F_, axis=0))
