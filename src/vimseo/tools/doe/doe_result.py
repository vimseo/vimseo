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

from dataclasses import dataclass
from json import dumps
from typing import TYPE_CHECKING

from gemseo.utils.string_tools import MultiLineString

from vimseo.tools.base_tool import BaseResult
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from gemseo.datasets.dataset import Dataset


@dataclass
class DOEResult(BaseResult):
    """The result of a DOE."""

    dataset: Dataset | None = None
    """The dataset resulting from the DOE."""

    def __str__(self):
        msg = MultiLineString()
        msg.add(dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder))
        msg.add("")
        msg.add(
            "============================= DOE Tool Results ========================="
        )
        msg.add(str(self.dataset))
        return str(msg)
