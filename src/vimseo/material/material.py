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

"""Formalisation of a material.

A material is composed of properties. At instantiation of a material, a validation of the
arguments passed to Material  constructor is automatically done (via
Pydantic.dataclasses).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.core.grammars.json_grammar import JSONGrammar
from gemseo.utils.string_tools import MultiLineString
from pydantic import Field
from pydantic import confloat
from pydantic import create_model

from vimseo.material.material_property import MaterialProperty
from vimseo.material.material_relation import MaterialRelation
from vimseo.utilities.distribution import DEFAULT_MIN_MAX
from vimseo.utilities.distribution import DistributionParameters
from vimseo.utilities.json_grammar_utils import BaseJsonIO
from vimseo.utilities.json_grammar_utils import load_default_inputs
from vimseo.utilities.json_grammar_utils import load_input_bounds

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from numbers import Number


class Material(BaseJsonIO):
    """A stochastic material.

    It can be used as a deterministic material, where the properties have a given value.
    Probability distribution can be associated to some material properties, such that a
    probabilistic parameter space can be defined from this material.
    """

    name: str
    description: str = ""
    material_relations: list[MaterialRelation] = Field(default_factory=list)

    @property
    def properties(self):
        """The material properties."""
        props = []
        for mat_rel in self.material_relations:
            for prop in mat_rel.properties:
                props.append(prop)  # noqa: PERF402
        return props

    @property
    def name_to_property(self):
        """The mapping between property names and the corresponding property."""
        return {prop.name: prop for prop in self.properties}

    def get_property(self, relation_name: str, property_name: str):
        """Get a material property in a given material relation."""
        material_relations = [
            mat_rel
            for mat_rel in self.material_relations
            if mat_rel.name == relation_name
        ]
        if len(material_relations) != 1:
            msg = f"No material relation with name {relation_name}."
            raise ValueError(msg)
        properties = [
            prop
            for prop in material_relations[0].properties
            if prop.name == property_name
        ]
        if len(properties) != 1:
            msg = (
                f"No material property with name {property_name} found in "
                f"material relation {relation_name}."
            )
            raise ValueError(msg)
        return properties[0]

    def to_json_schema(self, dir_path: Path | str = "", file_name: str = "") -> None:
        """Write the material as a JSON schema.

        The JSON schema is a full translation of the Pydantic model.

        Args:
            dir_path: The directory path under which to write the JSON file.
                By default, the current working directory is considered.
            file_name: The name of the JSON schema file.
                By default, the name is the material name suffixed by ``_grammar``.
        """
        dir_path = Path.cwd() if dir_path == "" else dir_path
        file_path = f"{self.name}_grammar.json" if file_name == "" else file_name
        json_schema = json.dumps(self.model_json_schema(), indent=4)
        Path(dir_path / file_path).write_text(json_schema)

    def to_legacy_json_schema(
        self, write: bool = False, dir_path: Path | str = "", file_name: str = ""
    ) -> None:
        """Write the material as a legacy JSON schema.

        The legacy JSON schema (as used before 21/08/2024 to define a material)
        is a simplified version of the full Pydantic model.
        It contains only the material property type and bounds, if defined.

        Args:
            dir_path: The directory path under which to write the JSON file.
                By default, the current working directory is considered.
            file_name: The name of the JSON schema file.
                By default, the name is the material name suffixed by ``_grammar``.
        """
        fields = {}
        for mat_rel in self.material_relations:
            for prop in mat_rel.properties:
                fields[prop.name] = (
                    list[confloat(le=prop.upper_bound, ge=prop.lower_bound)],
                    Field(description=prop.description),
                )
        model = create_model(f"{self.name}Legacy", **fields)
        json_schema = model.model_json_schema()
        if write:
            dir_path = Path.cwd() if dir_path == "" else dir_path
            file_name = (
                f"{self.name}_legacy_grammar.json" if file_name == "" else file_name
            )
            Path(dir_path / file_name).write_text(json.dumps(json_schema, indent=4))
        return json_schema

    @property
    def uncertain_variables(self):
        """The names of the variables to which a distribution (not the default empty one)
        is associated."""
        return [prop.name for prop in self.properties if prop.distribution.name != ""]

    def update_from_dict(self, values: Mapping[str, Number], relation_name: str = ""):
        """Update the properties from a dictionary of property name to values.

        If the property is stochastic, the mean value of the distribution is made equal
        to the new value, keeping other distribution parameters equal.
        """

        material_relations = (
            self.material_relations
            if relation_name == ""
            else [
                mat_rel
                for mat_rel in self.material_relations
                if mat_rel.name == relation_name
            ]
        )
        for name, value in values.items():
            for material_relation in material_relations:
                for prop in material_relation.properties:
                    if prop.name == name:
                        prop.value = value
                        # TODO identify uncertain properties in another way than by
                        #  this indirect check
                        if prop.distribution.name != "":
                            if prop.distribution.name == "Normal":
                                prop.distribution.sigma *= value / prop.distribution.mu
                                prop.distribution.mu = value
                            elif prop.distribution.name == "Uniform":
                                pass
                                # delta = value - 0.5 * (
                                #     prop.distribution.upper + prop.distribution.lower
                                # )
                                # prop.distribution.lower += delta
                                # prop.distribution.upper += delta
                            else:
                                msg = (
                                    f"Only deterministic, Normal and Uniform distributions "
                                    f"properties can be updated. "
                                    f"You are trying to update "
                                    f"variable {prop.name} having a "
                                    f"{prop.distribution.name} distribution."
                                )
                                raise ValueError(msg)

    # def update_from_dict(self, values: Mapping[str, Number]):
    #     """Set deterministic values from a dictionary."""
    #
    #     for name, value in values.items():
    #         for material_relation in self.material_relations:
    #             for prop in material_relation.properties:
    #                 if prop.name == name:
    #                     prop.value = (
    #                         value[0]
    #                         if isinstance(value, ndarray) and len(value) == 1
    #                         else value
    #                     )

    def update_from_parameter_space(self, parameter_space: ParameterSpace):
        """Set distributions of properties from a parameter space.

        Note:
            The deterministic values are not updated.
        """
        name_to_property = {
            prop.name: prop
            for mat_rel in self.material_relations
            for prop in mat_rel.properties
        }
        for name, distribution in parameter_space.distributions.items():
            if name in name_to_property:
                p = name_to_property[name]
                distribution = DistributionParameters(
                    **distribution.marginals[0].settings
                )
                p.distribution = distribution
                p.distribution.lower_bound = p.lower_bound
                p.distribution.upper_bound = p.upper_bound

    def to_parameter_space(self, variable_names: Iterable[str] = ()):
        """Return the material as a parameter space.

        The parameter space contains only the uncertain variables.
        """
        variable_names = (
            self.uncertain_variables if len(variable_names) == 0 else variable_names
        )
        parameter_space = ParameterSpace()
        for prop in self.properties:
            if prop.name in variable_names:
                if prop.name in self.uncertain_variables:
                    parameter_space.add_random_variable(
                        prop.name,
                        f"OT{prop.distribution.name}Distribution",
                        settings=prop.distribution,
                    )
                else:
                    parameter_space.add_variable(
                        name=prop.name,
                        value=prop.value,
                        lower_bound=prop.lower_bound,
                        upper_bound=prop.upper_bound,
                    )
        return parameter_space

    def get_values_as_dict(self) -> Mapping[str, float]:
        """Return the material property values as a mapping.

        Return: A mapping of property name to their value.
        """
        return {
            prop.name: prop.value
            for material_relation in self.material_relations
            for prop in material_relation.properties
        }

    def __str__(self):
        text = MultiLineString()
        text.add(self.name)
        text.add("Material relations:")
        text.add("")
        for mat_rel in self.material_relations:
            text.indent()
            text.add(mat_rel.name)
            for prop in mat_rel.properties:
                text.add(prop.name)
                text.indent()
                text.add(f"Default value: {prop.value}")
                text.add("Distribution:")
                text.add(str(prop.distribution))
                text.dedent()
                text.add("")
            text.dedent()
        return str(text)


def create_material_from_legacy_grammar(
    material_name: str,
    file_path: Path,
    default_values: Mapping[str:float] | None = None,
):
    """A util function to create a material from a legacy material JSON grammar (approach
    used before 21/08/2024).

    Args:
        material_name: The name of the material.
            Only used when exporting the new material.
        file_path: The path to the legacy JSON grammar file.
        default_values: A mapping of variable name
            to the default material property value.
            If default values are defined in the JSON grammar, they are considered
            but are updated by ``default_values``.
    """
    material_relation_to_names = None
    grammar = JSONGrammar("material")
    grammar.update_from_file(file_path)
    lower_bounds, upper_bounds, input_space = load_input_bounds(grammar)
    default_values_ = load_default_inputs(grammar)
    if default_values is not None:
        default_values_.update(default_values)
    if not material_relation_to_names:
        properties = []
        for name in input_space:
            lower_bound = lower_bounds.get(name, -DEFAULT_MIN_MAX)
            upper_bound = upper_bounds.get(name, DEFAULT_MIN_MAX)
            properties.append(
                MaterialProperty(
                    name=name,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound,
                    value=default_values_[name],
                )
            )

        mat_rel = MaterialRelation(
            name="DefaultMaterialRelation", properties=properties
        )
    return Material(name=material_name, material_relations=[mat_rel])
