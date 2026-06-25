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
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING

from gemseo.utils.string_tools import MultiLineString

from vimseo.tools.base_tool import BaseResult
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Mapping

    from gemseo.uncertainty.sensitivity.base_sensitivity_analysis import (
        BaseSensitivityAnalysis,
    )

LOGGER = logging.getLogger(__name__)


@dataclass
class SensitivityResult(BaseResult):
    """The result of a sensitivity analysis."""

    analysis: BaseSensitivityAnalysis | None = None
    """The sensitivity analysis."""

    indices: BaseSensitivityAnalysis.SensitivityIndices = field(default=None)
    """The indices of the sensitivity analysis."""

    variable_dimensions: Mapping[str, int] = field(default_factory=dict)

    def __str__(self):
        text = MultiLineString()
        text.add("Results of a sensitivity analysis.")
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        text.add("")
        text.add("Input variables by decreasing order of influence:")
        text.indent()
        for name in self.analysis.default_output_names:
            text.add(f"For output {name}: {self.analysis.sort_input_variables(name)}.")
        text.dedent()
        text.add("Sensitivity indices:")
        text.indent()
        for index_name in self.indices.__annotations__:
            text.add(f"Index {index_name}")
            text.indent()
            for name in self.analysis.default_output_names:
                text.add(f"{name}: {getattr(self.indices, index_name)[name]}")
            text.dedent()
        return str(text)
