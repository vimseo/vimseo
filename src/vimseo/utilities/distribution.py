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

from json import dumps

from gemseo.uncertainty.distributions.base_distribution import DistributionSettings
from gemseo.utils.string_tools import MultiLineString
from pydantic import ConfigDict

from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

DEFAULT_MIN_MAX = 1e12


class DistributionParameters(DistributionSettings):
    """Parameters representing a distribution."""

    ConfigDict(extra="forbid")

    name: str = ""

    def __str__(self):
        text = MultiLineString()
        text.indent()
        text.add(self.name)
        text.indent()
        text.indent()
        text.add("Parameters:")
        text.add(
            dumps(self.model_dump(), sort_keys=True, indent=10, cls=EnhancedJSONEncoder)
        )
        text.dedent()
        text.dedent()
        text.dedent()
        return str(text)
