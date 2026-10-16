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
"""The conversion of sensitivity indices into tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import atleast_1d
from pandas import DataFrame

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from gemseo.typing import RealArray


def flatten_components(values: Mapping[str, RealArray]) -> dict[str, float]:
    """Flatten the values of the input variables into values of input components.

    Args:
        values: The values of the input variables.

    Returns:
        The values of the input components, e.g. ``"x[1]"`` for a vector variable.
    """
    flat_values = {}
    for name, value in values.items():
        value = atleast_1d(value).ravel()
        if value.size == 1:
            flat_values[name] = float(value[0])
        else:
            flat_values.update({f"{name}[{j}]": float(v) for j, v in enumerate(value)})

    return flat_values


def indices_to_dataframe(
    indices: Mapping[str, Sequence[Mapping[str, RealArray] | None]],
) -> DataFrame:
    """Convert sensitivity indices of a kind into a table.

    Args:
        indices: The sensitivity indices of a kind,
            as ``{output_name: [{input_name: values}]}``
            where the list has an item per output component,
            ``None`` for a constant output component,
            and ``values`` has an item per input component.

    Returns:
        The indices, with a row per input component
        and a column per non-constant output component,
        e.g. ``"y[1]"`` for a vector output.
    """
    columns = {}
    for output_name, components in indices.items():
        for i, component in enumerate(components):
            if component is None:
                continue

            column_name = output_name if len(components) == 1 else f"{output_name}[{i}]"
            columns[column_name] = flatten_components(component)

    return DataFrame(columns)
