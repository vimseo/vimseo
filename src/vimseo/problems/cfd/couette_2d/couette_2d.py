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

# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import ClassVar

from numpy import atleast_1d

from vimseo.core.pre_run_post_model import PreRunPostModel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

LOGGER = logging.getLogger(__name__)

DEFAULT_INPUT_DATA = {
    "mu": atleast_1d(0.417),
    "prandtl": atleast_1d(0.72),
    "cp": atleast_1d(1005.0),
    "dt": atleast_1d(4e-5),
    "dx": atleast_1d(0.25),
    "u_w": atleast_1d(70.0),
}


class PyFRModel(PreRunPostModel):
    """A research CFD model solved by PyFR."""

    default_cache_type = "SimpleCache"
    default_grammar_type = "PydanticGrammar"

    PRE_PROC_FAMILY = "PrePyFR"

    RUN_FAMILY = "RunPyFR"

    POST_PROC_FAMILY = "PostPyFR"

    FIELDS_FROM_FILE: ClassVar[Mapping[str, str]] = {
        "solution": r"^couette-flow-+\d+\.vtu$"
    }

    CURVES: ClassVar[Sequence[tuple[str]]] = [
        ("line_y", "line_density_009"),
        ("line_y", "line_velocity_0_009"),
        ("line_y", "line_velocity_1_009"),
        ("line_y", "line_pressure_009"),
    ]
