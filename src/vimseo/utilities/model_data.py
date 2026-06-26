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
from typing import Any

from strenum import StrEnum

if TYPE_CHECKING:
    from collections.abc import Mapping


class MetricVariableType(StrEnum):
    """The type of variable on which calibration is performed."""

    SCALAR = "SCALAR"
    VECTOR = "VECTOR"
    CURVE = "CURVE"


def decapsulate_length_one_array(data: Mapping[str, Any]):
    """Convert length one array to its value."""
    data = data.copy()

    # de-capsulate useless arrays to scalars
    # data = decapsulate_length_one_array(data)
    for k in data:
        # TODO use better condition to check for sequence (see mlflow_tracking sandbox)
        if hasattr(data[k], "__len__") and len(data[k]) == 1:
            data[k] = data[k][0]

    # cast original types into standard JSON serializable
    for k in data:
        if isinstance(data[k], dict):
            # recursivity on encapsulated dicts
            data[k] = encode_model_data(data[k])  # noqa : F821

    return data
