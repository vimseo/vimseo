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

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from json import dumps

from gemseo.disciplines.surrogate import SurrogateDiscipline
from gemseo.mlearning.core.quality.base_ml_algo_quality import BaseMLAlgoQuality
from gemseo.third_party.prettytable.prettytable import PrettyTable
from gemseo.utils.string_tools import MultiLineString
from numpy import ndarray

from vimseo.tools.base_result import BaseResult
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

QualitiesType = Mapping[str, Mapping[str, Mapping[str, type(BaseMLAlgoQuality)]]]


@dataclass
class SurrogateResult(BaseResult):
    """The result of a :class:`~.SurrogateTool`."""

    model: SurrogateDiscipline = None
    """The surrogate model."""

    # TODO use Surrogate.name?
    model_name: str = None
    """The name of the surrogate model."""

    qualities: QualitiesType = field(default_factory=dict)
    """The quality of the surrogate model for the selected measures and evaluation
    methods."""

    selection_qualities: Mapping[
        str, Mapping[str, Mapping[str, Mapping[str, ndarray[float]]]]
    ] = field(default_factory=dict)
    """The qualities of the candidate surrogate models for the selected measures and
    evaluation methods."""

    def __str__(self):
        """Returns a table showing the value of quality measures evaluated for the
        (selected) surrogate model. In case several evaluation methods were used, the
        corresponding values are listed.

        Rows of the returned table correspond to quality measures, while columns
        correspond to evaluation methods.

        Returns:
            A table formatted as a string with rows corresponding to quality
            measure and columns corresponding to evaluation methods.

        Raise:
            KeyError: When no surrogate model is available.
        """
        if len(self.qualities.keys()) > 0:
            measures = list(self.qualities.keys())
        else:
            msg = "No surrogate model is available."
            raise ValueError(msg)

        methods = list(self.qualities[measures[0]].keys())

        msg = MultiLineString()
        msg.add(dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder))
        msg.add(f"=========  Surrogate model: {self.model_name} =========")
        msg.add(" ")
        msg.add(f"{self.model.regression_model}")
        msg.add(" ")
        msg.add("----------- Summary of Surrogate Quality ---------------")

        columns = ["Measure", *methods]
        table = PrettyTable(field_names=columns)

        for measure in measures:
            row = [measure] + [self.qualities[measure][meth] for meth in methods]
            table.add_row(row)

        msg.add(table.get_string())
        msg.add("-----------------------------------------------------------")
        if len(list(self.selection_qualities.keys())):
            candidates = list(self.selection_qualities.keys())
            measures = list(self.selection_qualities[candidates[0]].keys())
            methods = list(self.selection_qualities[candidates[0]][measures[0]].keys())
            msg.add("-------- Qualities of all candidate algorithms ----------")

            columns = ["Measure", "Algo", *methods]
            table = PrettyTable(field_names=columns)

            for measure in measures:
                col1 = f"{measure}"
                for algo in candidates:
                    row = [col1, f"{algo}"] + [
                        self.selection_qualities[algo][measure][meth]
                        for meth in methods
                    ]
                    table.add_row(row)
                    col1 = ""
            msg.add(table.get_string())
            msg.add("-----------------------------------------------------------")

        return str(msg)
