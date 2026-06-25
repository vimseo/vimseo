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

import logging
from typing import TYPE_CHECKING
from typing import ClassVar

from vimseo.core.pre_run_post_model import PreRunPostModel
from vimseo.material_lib import MATERIAL_LIB_DIR

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class BendingTestAnalytical(PreRunPostModel):
    """This model represents a straight beam subjected to different bending load cases
    and boundary conditions. It is based on Bernouilli hypothesis.

    Possible load cases are:
    - Cantilever: clamped at one end, and displacement applied on the beam according to
    the relative_dplt_location attribute.
    - ThreePoints: displacement applied on the beam according to the
    relative_dplt_location attribute and support location according to the
    relative_support_location attribute.

    Input parameters are geometry of the section, Young's modulus, length of the beam,
    the relative displacement location, the relative support location (for the
    ThreePoints load case) and the load case name.

    Output parameters are the maximum displacement in the direction of the loading, the
    location of this maximum displacement, the maximum reaction forces, the displacement
    and the moment fields and the displacement at the maximum reaction forces.

    We suppose that positive force is upwards. The imposed displacement is downwards.
    """

    SUMMARY = " An analytical model for the bending of a parallelepipedic beam"
    PRE_PROC_FAMILY = "PreBendingTestAnalytical"
    RUN_FAMILY = "RunBendingTestAnalytical"
    POST_PROC_FAMILY = "PostBendingTestAnalytical"
    MATERIAL_FILE = MATERIAL_LIB_DIR / "Ta6v.json"
    CURVES: ClassVar[Sequence[tuple[str]]] = [
        ("dplt_grid", "dplt"),
        ("moment_grid", "moment"),
    ]

    _MATERIAL_GRAMMAR_FILE: ClassVar[Path | str] = (
        MATERIAL_LIB_DIR / "Ta6v_grammar.json"
    )
    _LOAD_CASE_DOMAIN = "Beam"
