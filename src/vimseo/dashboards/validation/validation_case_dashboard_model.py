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

from typing import TYPE_CHECKING

from numpy import array
from strenum import StrEnum

if TYPE_CHECKING:
    from pandas import DataFrame


def initialize(session_state):

    variables = {}

    for name, default in variables.items():
        if name not in session_state:
            session_state[name] = default


class NominalDataAdder(StrEnum):
    NONE = "none"
    LAYUP = "layup"


def nominal_space_adder(
    df: DataFrame,
    adder_name: NominalDataAdder = NominalDataAdder.NONE,
    layups=(),
) -> list[str]:
    """Add variables to a dataframe based on pre-defined relationships."""
    if adder_name == NominalDataAdder.LAYUP:
        added_keys = [
            "ply_ratio_0",
            "ply_ratio_45",
            "ply_ratio_90",
            "lamination_parameters_A_0",
            "lamination_parameters_A_2",
            "lamination_parameters_B_1",
            "lamination_parameters_D_0",
            "lamination_parameters_D_1",
            "lamination_parameters_D_2",
        ]

        from vims_composites.utilities.lamination_parameters import (
            get_lamination_parameters,
        )
        from vims_composites.utilities.lamination_parameters import (
            get_ply_ratio_0_45_90,
        )

        ply_ratios = array([get_ply_ratio_0_45_90(layup) for layup in layups]).T
        lam_params = array([get_lamination_parameters(layup) for layup in layups]).T
        lam_param_a = lam_params[0]
        lam_param_b = lam_params[1]
        lam_param_d = lam_params[2]
        df["ply_ratio_0"] = ply_ratios[0]
        df["ply_ratio_45"] = ply_ratios[1]
        df["ply_ratio_90"] = ply_ratios[2]
        df["lamination_parameters_A_0"] = lam_param_a[0]
        df["lamination_parameters_A_2"] = lam_param_a[2]
        df["lamination_parameters_B_1"] = lam_param_b[1]
        df["lamination_parameters_D_0"] = lam_param_d[0]
        df["lamination_parameters_D_1"] = lam_param_d[1]
        df["lamination_parameters_D_2"] = lam_param_d[2]

        return added_keys

    return ()
