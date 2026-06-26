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

from pathlib import Path

import pytest
from gemseo.core.grammars.json_grammar import JSONGrammar

from vimseo.io.space_io import SpaceToolFileIO
from vimseo.material.material import Material
from vimseo.material.material import create_material_from_legacy_grammar
from vimseo.material.material_property import MaterialProperty
from vimseo.material.material_relation import MaterialRelation
from vimseo.material.metadata import MaterialMetadata
from vimseo.material.test_references import MATERIAL_TEST_REFERENCES
from vimseo.material_lib import MATERIAL_LIB_DIR
from vimseo.utilities.distribution import DistributionParameters


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        MaterialMetadata(misc={"foo1": "bar", "foo2": 1.0, "foo3": [1.0, 2.0]}),
    ],
)
@pytest.mark.parametrize(
    "distribution",
    [
        DistributionParameters(name="Normal", mu=1e5, sigma=1e2),
    ],
)
def test_material_relation(tmp_wd, metadata, distribution):
    """Check that a material relation can be exported to json file and loaded from a json
    file."""
    prop = MaterialProperty(
        name="young_modulus",
        value=1e5,
        lower_bound=9e4,
        upper_bound=1.1e5,
        distribution=distribution,
    )
    if metadata:
        mat_rel_1 = MaterialRelation(
            tag="Ta6v_v1",
            name="Ta6v",
            metadata=metadata,
            properties=[prop],
        )
    else:
        mat_rel_1 = MaterialRelation(
            tag="Ta6v_v1",
            name="Ta6v",
            properties=[prop],
        )
    # Override datetime to be able to compare the two material relations.
    mat_rel_1.metadata.generic["datetime"] = ""
    file_name = "mat_rel_1.json"
    mat_rel_1.to_json(file_name=file_name)
    mat_rel_loaded = MaterialRelation.from_json(file_name)
    mat_rel_loaded.metadata.generic["datetime"] = ""
    assert str(mat_rel_1) == str(mat_rel_loaded)


def test_material(tmp_wd):
    """Check that a material can be serialized to a JSON file and reloaded."""
    mat_rel_1 = MaterialRelation(
        tag="Ta6v_v1",
        name="Ta6v_elastic_iso",
        properties=[
            MaterialProperty(
                name="young_modulus",
                value=2.1e5,
                lower_bound=1.9e5,
                upper_bound=2.3e5,
                distribution=DistributionParameters(name="Normal", mu=2.1e5, sigma=1e2),
            ),
            MaterialProperty(
                name="nu_p",
                value=0.3,
                distribution=DistributionParameters(name="Normal", mu=0.3, sigma=0.02),
            ),
        ],
    )
    material = Material(name="Ta6v", material_relations=[mat_rel_1])

    assert [prop.name for prop in material.properties] == ["young_modulus", "nu_p"]

    file_name = "material.json"
    material.to_json(file_name=file_name)
    material_loaded = Material.from_json(file_name)

    assert material == material_loaded
    assert material.get_values_as_dict() == material_loaded.get_values_as_dict()

    legacy_schema = material_loaded.to_legacy_json_schema(write=True)

    ref_legacy_grammar = JSONGrammar("ref_legacy_material")
    ref_legacy_grammar.update_from_file(
        MATERIAL_TEST_REFERENCES / "Ta6v_legacy_grammar.json"
    )

    assert ref_legacy_grammar.schema["properties"] == legacy_schema["properties"]


def test_uncertain_variables():
    """Check that a material with uncertain properties can return its property names and
    can be exported as a parameter space."""
    mat_rel_1 = MaterialRelation(
        tag="Ta6v_v1",
        name="Ta6v_elastic_iso",
        properties=[
            MaterialProperty(
                name="young_modulus",
                value=2.1e5,
                lower_bound=1.9e5,
                upper_bound=2.3e5,
                distribution=DistributionParameters(name="Normal", mu=2.1e5, sigma=1e2),
            ),
            MaterialProperty(
                name="nu_p",
                value=0.3,
            ),
        ],
    )
    material = Material(name="Ta6v", material_relations=[mat_rel_1])
    assert material.uncertain_variables == ["young_modulus"]

    parameter_space = material.to_parameter_space()
    assert parameter_space.variable_names == ["young_modulus"]


def test_update_from_parameter_space():
    """Check that a stochastic material can be defined from a parameter space."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Mock.json")
    parameter_space = (
        SpaceToolFileIO()
        .read(MATERIAL_TEST_REFERENCES / "Mock_E1_distribution.json")
        .parameter_space
    )
    material.update_from_parameter_space(parameter_space)
    assert material.name_to_property["E1"].distribution == DistributionParameters(
        **parameter_space.distributions["E1"].marginals[0].settings
    )


def test_update_deterministic_material():
    """Check that a deterministic values of a material can updated."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Mock.json")
    print(material)
    assert material.get_values_as_dict()["E1"] == 1.5e5
    new_e1 = 1.4e5
    material.update_from_dict({"E1": new_e1})
    assert material.get_values_as_dict()["E1"] == new_e1


def test_update_stochastic_material():
    """Check that a stochastic material property can be updated to a new value."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
    prop = material.get_property("Ta6v_elastic_iso", "young_modulus")
    mu = prop.distribution.mu
    sigma = prop.distribution.sigma
    new_value = 2.2e5
    material.update_from_dict({"young_modulus": new_value})
    # TODO add a get_property()
    assert prop.name == "young_modulus"
    assert prop.value == new_value
    assert prop.distribution.name == "Normal"
    assert prop.distribution.mu == new_value
    assert prop.distribution.sigma == pytest.approx(sigma * new_value / mu)


def test_get_property_unknown_relation_raises():
    """Getting a property from an unknown material relation raises."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
    with pytest.raises(ValueError, match="No material relation"):
        material.get_property("UnknownRelation", "young_modulus")


def test_get_property_unknown_property_raises():
    """Getting an unknown property from a known relation raises."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
    with pytest.raises(ValueError, match="No material property"):
        material.get_property("Ta6v_elastic_iso", "unknown_property")


def test_to_json_schema(tmp_wd):
    """A material can be exported as a JSON schema file."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
    material.to_json_schema()
    assert Path(f"{material.name}_grammar.json").is_file()


def test_update_uniform_distribution_keeps_parameters():
    """Updating a Uniform-distributed property updates the value but not the
    distribution parameters."""
    prop = MaterialProperty(
        name="x",
        value=1.0,
        lower_bound=0.0,
        upper_bound=2.0,
        distribution=DistributionParameters(name="Uniform"),
    )
    material = Material(
        name="m", material_relations=[MaterialRelation(name="r", properties=[prop])]
    )
    material.update_from_dict({"x": 1.5})
    assert prop.value == 1.5  # noqa: RUF069
    assert prop.distribution.name == "Uniform"


def test_update_unsupported_distribution_raises():
    """Updating a property with an unsupported distribution raises."""
    prop = MaterialProperty(
        name="x",
        value=1.0,
        distribution=DistributionParameters(name="Triangular"),
    )
    material = Material(
        name="m", material_relations=[MaterialRelation(name="r", properties=[prop])]
    )
    with pytest.raises(ValueError, match="Only deterministic, Normal and Uniform"):
        material.update_from_dict({"x": 2.0})


def test_to_parameter_space_includes_deterministic_variable():
    """A deterministic property explicitly requested is added as a design variable."""
    mat_rel = MaterialRelation(
        name="r",
        properties=[
            MaterialProperty(
                name="young_modulus",
                value=2.1e5,
                lower_bound=1.9e5,
                upper_bound=2.3e5,
                distribution=DistributionParameters(name="Normal", mu=2.1e5, sigma=1e2),
            ),
            MaterialProperty(name="nu_p", value=0.3, lower_bound=0.2, upper_bound=0.4),
        ],
    )
    material = Material(name="m", material_relations=[mat_rel])
    parameter_space = material.to_parameter_space(
        variable_names=["young_modulus", "nu_p"]
    )
    assert set(parameter_space.variable_names) == {"young_modulus", "nu_p"}


def test_create_material_from_legacy_grammar():
    """A material can be created from a legacy JSON grammar and default values."""
    material = create_material_from_legacy_grammar(
        "Ta6v",
        MATERIAL_TEST_REFERENCES / "Ta6v_legacy_grammar.json",
        default_values={"young_modulus": 2.1e5, "nu_p": 0.3},
    )
    assert material.name == "Ta6v"
    values = material.get_values_as_dict()
    assert values["young_modulus"] == 2.1e5  # noqa: RUF069
    assert values["nu_p"] == 0.3  # noqa: RUF069
