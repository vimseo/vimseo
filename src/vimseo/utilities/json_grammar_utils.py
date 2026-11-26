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
    from typing import Any

    from gemseo.core.grammars.base_grammar import BaseGrammar

    from vimseo.material.material import Material

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
    properties = grammar.schema.get("properties", {})
    for key in properties:
        if properties[key].get("type") == "array":
            items = properties[key].get("items", {})
            var_type = items.get("type")
            lower_bound = items.get("minimum")
            if lower_bound is not None:
                lower_bounds[key] = lower_bound
            if var_type == "number":
                if lower_bound is not None:
                    input_space[key] = [lower_bound]
                else:
                    input_space[key] = [-inf]

            upper_bound = items.get("maximum")
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


def read_json_grammar(file_path: str | Path, name: str = "") -> JSONGrammar:
    """Read a JSON grammar file.

    The schema of the file is read as the one of an object, even without
    ``"type": "object"``, so that its ``properties`` are the variables of the grammar.

    Args:
        file_path: The path to the JSON grammar file.
        name: The name of the grammar. By default, the path to the file.

    Returns:
        The JSON grammar.

    Raises:
        ValueError: When the file is not a valid JSON schema.
    """
    grammar = JSONGrammar(name or str(file_path))
    grammar.update_from_schema({"type": "object"})
    try:
        grammar.update_from_file(file_path, merge=True)
    except (ValueError, RuntimeError, AttributeError) as error:
        # GEMSEO raises a JSONDecodeError (a ValueError) for an invalid JSON file, a
        # RuntimeError for an unknown type, and an AttributeError for a JSON file
        # which is not an object.
        msg = f"The JSON grammar file {file_path} is not a valid JSON schema: {error}"
        raise ValueError(msg) from error
    return grammar


def check_grammar_restriction(reference: JSONGrammar, grammar: JSONGrammar) -> None:
    """Check that a JSON grammar can replace a reference grammar.

    The grammar shall declare all the variables of the reference grammar and only
    restrict them.

    Args:
        reference: The reference grammar.
        grammar: The grammar replacing the reference grammar,
            e.g. read from a file by :func:`read_json_grammar`.

    Raises:
        ValueError: When the grammar declares a variable unknown to the reference
            grammar, misses a variable of the reference grammar, changes the type of a
            variable, or has a looser ``minimum`` or ``maximum`` than the reference one.
    """
    names, reference_names = set(grammar.names), set(reference.names)
    errors = []
    unknown_names = sorted(names - reference_names)
    if unknown_names:
        errors.append(f"unknown variables {unknown_names}")
    missing_names = sorted(reference_names - names)
    if missing_names:
        errors.append(f"missing variables {missing_names}")
    properties = grammar.schema.get("properties", {})
    reference_properties = reference.schema.get("properties", {})
    lower_bounds, upper_bounds, _ = load_input_bounds(grammar)
    reference_lower_bounds, reference_upper_bounds, _ = load_input_bounds(reference)
    for name in sorted(names & reference_names):
        prop_type = _get_type(properties[name])
        reference_type = _get_type(reference_properties[name])
        if prop_type != reference_type:
            errors.append(f"{name}: type {prop_type} instead of {reference_type}")
            continue
        lower_bound = lower_bounds.get(name)
        reference_lower_bound = reference_lower_bounds.get(name)
        if reference_lower_bound is not None and (
            lower_bound is None or lower_bound < reference_lower_bound
        ):
            errors.append(
                f"{name}: minimum {lower_bound} looser than {reference_lower_bound}"
            )
        upper_bound = upper_bounds.get(name)
        reference_upper_bound = reference_upper_bounds.get(name)
        if reference_upper_bound is not None and (
            upper_bound is None or upper_bound > reference_upper_bound
        ):
            errors.append(
                f"{name}: maximum {upper_bound} looser than {reference_upper_bound}"
            )
    if errors:
        msg = (
            f"The JSON grammar {grammar.name} shall declare all the variables of the "
            f"grammar {reference.name} and only restrict them: {'; '.join(errors)}."
        )
        raise ValueError(msg)


def _get_type(prop: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Return the type of a property of a JSON schema and the type of its items.

    Args:
        prop: The property.

    Returns:
        The type of the property and the type of its items, ``None`` when undefined.
    """
    return prop.get("type"), prop.get("items", {}).get("type")


def check_material_bounds(material: Material, grammar: JSONGrammar) -> None:
    """Check that the bounds of a material are within those of a JSON grammar.

    Only the material properties with a bound in the grammar are checked, so that an
    uncertain space built from the material yields values valid for the grammar.

    Args:
        material: The material.
        grammar: The JSON grammar.

    Raises:
        ValueError: When a material property has a looser bound than the grammar,
            or a value out of the grammar bounds.
    """
    lower_bounds, upper_bounds, _ = load_input_bounds(grammar)
    errors = []
    for prop in material.properties:
        if prop.name in lower_bounds:
            lower_bound = lower_bounds[prop.name]
            if prop.lower_bound < lower_bound:
                errors.append(
                    f"{prop.name}: lower bound {prop.lower_bound} looser than "
                    f"{lower_bound}"
                )
            if prop.value < lower_bound:
                errors.append(f"{prop.name}: value {prop.value} below {lower_bound}")
        if prop.name in upper_bounds:
            upper_bound = upper_bounds[prop.name]
            if prop.upper_bound > upper_bound:
                errors.append(
                    f"{prop.name}: upper bound {prop.upper_bound} looser than "
                    f"{upper_bound}"
                )
            if prop.value > upper_bound:
                errors.append(f"{prop.name}: value {prop.value} above {upper_bound}")
    if errors:
        msg = (
            f"The material {material.name} shall be within the bounds of the grammar "
            f"{grammar.name}: {'; '.join(errors)}."
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
