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

from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from gemseo.core.grammars.json_grammar import JSONGrammar

from vimseo.material.material import Material
from vimseo.material_lib import MATERIAL_LIB_DIR
from vimseo.utilities.datasets import SEP

PATH_TO_MATERIAL_DOC_SUBDIR = Path("docs/references/materials")


@dataclass
class PropertyAttributes:
    description: str = ""
    unit: str = "none"
    category: str = "Undefined"
    material_relation: str = ""
    default_value: float = np.nan
    distribution: str = "Undefined"


def create_material_description_table(
    material_lib_dir: Path, material_name: str
) -> pd.DataFrame:
    """Create a table describing a material.

    The table are saved as csv files in the material section of the documentation.
    """
    grammar = JSONGrammar(
        material_name, material_lib_dir / f"{material_name}_grammar.json"
    )
    material = Material.from_json(material_lib_dir / f"{material_name}.json")

    name_to_attributes = {}
    for rel in material.material_relations:
        for prop in rel.properties:
            raw_description = grammar.schema["properties"][prop.name]["description"]
            attributes = PropertyAttributes()
            description = raw_description
            if "{{" in raw_description and "}}" in raw_description:
                attributes.unit = raw_description.split("{{")[1].split("}}")[0]
                description = description.split("{{")[0]
            if "[" in raw_description and "]" in raw_description:
                attributes.category = raw_description.split("[")[1].split("]")[0]
                description = description.split("]")[1]
            attributes.description = description.strip()
            attributes.material_relation = rel.name
            attributes.default_value = prop.value
            if prop.distribution.name != "":
                attributes.distribution = prop.distribution.name
            name_to_attributes[prop.name] = attributes

    attribute_name_to_value = defaultdict(list)
    for name, attributes in name_to_attributes.items():
        attribute_name_to_value["name"].append(name)
        for name, value in asdict(attributes).items():
            attribute_name_to_value[name].append(value)

    df = pd.DataFrame.from_dict(attribute_name_to_value)
    df.to_csv(
        Path.cwd() / PATH_TO_MATERIAL_DOC_SUBDIR / f"{material_name}_properties.csv",
        sep=SEP,
    )
    return df


if __name__ == "__main__":
    for name in ["Ta6v"]:
        df = create_material_description_table(MATERIAL_LIB_DIR, name)
        print(df)
