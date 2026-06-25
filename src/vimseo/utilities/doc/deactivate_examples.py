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

"""Deactivate some runnable examples, because they require executables or prerequisites
not available locally."""

from __future__ import annotations

import glob
from pathlib import Path

import vimseo as vimseo_lib

VIMS_SRC_DIR = Path(vimseo_lib.__path__[0]).resolve()
RUNNABLE_DIR = VIMS_SRC_DIR / "../../docs/runnable_examples"

INPUT_PREFIX = ""
OUTPUT_PREFIX = "_"

EXAMPLES_TO_DEACTIVATE = [
    Path("01_models") / "plot_MockModelAbaqus_LC1.py",
    Path("01_models") / "plot_BendingTestFem*.py",
    Path("01_models") / "plot_EomsUmatUnitcell*.py",
    Path("01_models") / "plot_EomsUmatAbaqus*.py",
    Path("01_models") / "plot_EomsVumatUnitcell*.py",
    Path("01_models") / "plot_EomsVumatAbaqus*.py",
    Path("02_integrated_models") / "plot_01_basic_usage.py",
    Path("03_verification_vs_data") / "plot_bending_test_vs_data.py",
    Path("04_verification_vs_model_from_parameter_space")
    / "plot_bending_test_vs_analytical_from_parameter_space.py",
    Path("05_solution_verification") / "plot_bending_test_convergence.py",
]

if __name__ == "__main__":
    paths_to_prefix = [
        glob.glob(str(RUNNABLE_DIR / path.parent / f"{INPUT_PREFIX}{path.name}"))  # noqa: PTH207
        for path in EXAMPLES_TO_DEACTIVATE
    ]
    paths_to_prefix = [Path(p) for path_list in paths_to_prefix for p in path_list]
    print(f"Prefixing {paths_to_prefix} to deactivate examples.")
    for path in paths_to_prefix:
        path.rename(
            path.parent / f"{OUTPUT_PREFIX}{str(path.name)[len(INPUT_PREFIX) :]}"
        )
