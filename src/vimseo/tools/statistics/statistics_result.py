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

from collections import OrderedDict
from dataclasses import dataclass
from json import dumps

from gemseo.third_party.prettytable.prettytable import PrettyTable
from gemseo.uncertainty.statistics.base_statistics import BaseStatistics
from gemseo.utils.string_tools import MultiLineString
from pandas import DataFrame

from vimseo.tools.base_result import BaseResult
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder


@dataclass
class StatisticsResult(BaseResult):
    """The result of a statistics analysis."""

    analysis: BaseStatistics | None = None
    """The statistics analysis."""

    best_fitting_distributions: dict[str, str] | None = None

    statistics: OrderedDict | DataFrame | None = None
    """The reduced statistics."""

    def __str__(self):
        text = MultiLineString()
        text.add("Results of a Statistics analysis.")
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        variable_names = list(self.analysis.distributions.keys())
        table = PrettyTable(variable_names)
        table.add_row([
            self.analysis.distributions[name].value for name in variable_names
        ])
        text.add("")
        text.add("Best fitting distribution:")
        text.add(table.get_string())

        text.add("")
        text.add("Fitting matrix (goodness-of-fit measures):")
        text.add(self.analysis.get_fitting_matrix())
        text.add("")
        text.add("Statistics indicators:")
        text.add(repr(self.statistics))
        return str(text)
