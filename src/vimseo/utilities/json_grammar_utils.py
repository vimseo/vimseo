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
from gemseo.core.grammars.json_grammar import JSONGrammar
from gemseo.mlearning import MinMaxScaler
from numpy import array
from numpy import inf
from numpy import ndarray
from pandas import DataFrame
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from numbers import Number

    from gemseo.core.grammars.base_grammar import BaseGrammar

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


def to_json_grammar(grammar: BaseGrammar, name: str = "") -> JSONGrammar:
    """Return a grammar as a JSON grammar.

    Args:
        grammar: The grammar.
        name: The name of the JSON grammar. By default, the name of ``grammar``.

    Returns:
        A copy of ``grammar`` when it is a JSON grammar, with its bounds; otherwise
        a JSON grammar built from the types of its variables.
    """
    json_grammar = JSONGrammar(name or grammar.name)
    if isinstance(grammar, JSONGrammar):
        json_grammar.update(grammar)
    else:
        json_grammar.update_from_types(grammar._get_names_to_types())
    return json_grammar


def check_grammar_restriction(reference: JSONGrammar, file_path: str | Path) -> None:
    """Check that a JSON grammar file only restricts a reference grammar.

    Args:
        reference: The reference grammar.
        file_path: The path to the JSON grammar file.

    Raises:
        ValueError: When the file declares a variable unknown to the reference grammar,
            changes the type of a variable, or has a looser ``minimum`` or ``maximum``
            than the reference one.
    """
    properties = json.loads(Path(file_path).read_text(encoding="utf-8"))["properties"]
    reference_properties = reference.schema["properties"]
    errors = []
    unknown_names = sorted(properties.keys() - reference_properties.keys())
    if unknown_names:
        errors.append(f"unknown variables {unknown_names}")
    lower_bounds, upper_bounds, _ = load_input_bounds(reference)
    for name in sorted(properties.keys() & reference_properties.keys()):
        prop = properties[name]
        reference_prop = reference_properties[name]
        prop_type = (prop.get("type"), prop.get("items", {}).get("type"))
        reference_type = (
            reference_prop.get("type"),
            reference_prop.get("items", {}).get("type"),
        )
        if prop_type != reference_type:
            errors.append(f"{name}: type {prop_type} instead of {reference_type}")
            continue
        items = prop.get("items", {})
        lower_bound, upper_bound = items.get("minimum"), items.get("maximum")
        if name in lower_bounds and (
            lower_bound is None or lower_bound < lower_bounds[name]
        ):
            errors.append(
                f"{name}: minimum {lower_bound} looser than {lower_bounds[name]}"
            )
        if name in upper_bounds and (
            upper_bound is None or upper_bound > upper_bounds[name]
        ):
            errors.append(
                f"{name}: maximum {upper_bound} looser than {upper_bounds[name]}"
            )
    if errors:
        msg = (
            f"The JSON grammar {file_path} shall only restrict the grammar "
            f"{reference.name}: {'; '.join(errors)}."
        )
        raise ValueError(msg)


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        from gemseo.core.grammars.defaults import Defaults

        if isinstance(o, Defaults):
            return dict(o)
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
