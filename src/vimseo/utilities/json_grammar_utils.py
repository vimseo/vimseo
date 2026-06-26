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

import json
import logging
from dataclasses import asdict
from dataclasses import is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.mlearning import MinMaxScaler
from numpy import array
from numpy import inf
from numpy import ndarray
from pandas import DataFrame
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from numbers import Number

    from gemseo.core.grammars.json_grammar import JSONGrammar

LOGGER = logging.getLogger(__name__)


def load_input_bounds(
    grammar: JSONGrammar,
) -> tuple[Mapping[str, Number | list[Number]]]:
    """Return minimum and maximum bounds for variables of type ``array[number]`` in a
    JSON grammar.

    If no minimum (resp. maximum) is defined, the ``lower_bounds``
    (resp. ``upper_bound``) are empty dictionaries.
    This function also returns ``input_space`` attribute is also filled,
    only if the type of item is number.
    If no minimum (resp. maximum) is defined, -inf (resp. inf) is used as bound.

    Returns:
        Three dictionaries mapping variable name to lower bound, upper bound
        and input space
    """
    input_space = {}
    lower_bounds = {}
    upper_bounds = {}
    properties = grammar.schema["properties"]
    for key in properties:
        if properties[key]["type"] == "array":
            var_type = properties[key]["items"].get("type")
            lower_bound = properties[key]["items"].get("minimum")
            if lower_bound is not None:
                lower_bounds[key] = lower_bound
            if var_type == "number":
                if lower_bound is not None:
                    input_space[key] = [lower_bound]
                else:
                    input_space[key] = [-inf]

            upper_bound = properties[key]["items"].get("maximum")
            if upper_bound is not None:
                upper_bounds[key] = upper_bound
            if var_type == "number":
                if upper_bound is not None:
                    input_space[key].append(upper_bound)
                else:
                    input_space[key].append(inf)

    return lower_bounds, upper_bounds, input_space


def load_default_inputs(grammar: JSONGrammar) -> Mapping[str, float]:
    """Loads default inputs from a JSON grammar."""

    default_inputs = {}

    properties = grammar.schema["properties"]
    for key in properties:
        if properties[key]["type"] == "array":
            try:
                default_inputs[key] = array([properties[key]["items"]["default"]])
            except KeyError:
                # no default value defined in Json file
                LOGGER.debug(f"Default value is not defined for input key {key}.")
        elif properties[key]["type"] in ["string", "number"]:
            try:
                default_inputs[key] = properties[key]["default"]
            except KeyError:
                # no default value defined in Json file
                LOGGER.debug(f"Default value is not defined for input key {key}.")

    return default_inputs


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (int, np.integer)):
            return int(o)
        if isinstance(o, (int, np.floating)):
            return float(o)
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, ndarray):
            return o.tolist()
        if isinstance(o, MinMaxScaler):
            return repr(o)
        if isinstance(o, BaseModel):
            return dict(o)
        if isinstance(o, ParameterSpace):
            return str(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, DataFrame):
            return o.to_string()

        return super().default(o)


class EnhancedJSONEncoderArchive(EnhancedJSONEncoder):
    def encode(self, o, indent=0):
        # Custom layout of JSON, in order to make JSON actually readable
        if isinstance(o, list):
            # list printed on a single line
            return "[{}]".format(
                ",".join(self.encode(item, indent=indent + 4) for item in o)
            )
        if isinstance(o, dict):
            # dict printed with indentation (recursive if necessary)
            return (
                "{\n"
                + ",\n".join(
                    " " * indent
                    + f'     "{key}": {self.encode(value, indent=indent + 4)}'
                    for key, value in o.items()
                )
                + "\n"
                + indent * " "
                + "}"
            )
        return super().encode(o)


class BaseJsonIO(BaseModel):
    """A class adding export and read values from a json file."""

    @classmethod
    def from_json(cls, file_name: str | Path, dir_path: Path | str = ""):
        dir_path = Path.cwd() if dir_path == "" else dir_path
        return cls.model_validate_json(Path(dir_path / file_name).read_text())

    def to_json(self, dir_path: Path | str = "", file_name: str | Path = ""):
        dir_path = Path.cwd() if dir_path == "" else dir_path
        file_name = f"{self.name}.json" if file_name == "" else file_name
        Path(dir_path / file_name).write_text(self.model_dump_json(indent=True))
