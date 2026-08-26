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

"""Discovery of the materials a model can be built with."""

from __future__ import annotations

import json

import pytest

from vimseo.api import create_model
from vimseo.api import get_available_materials
from vimseo.material.material import Material
from vimseo.material.material_registry import compatible_materials
from vimseo.material.material_registry import default_material_name
from vimseo.material.material_registry import grammar_name_of
from vimseo.material.material_registry import material_lib_directories
from vimseo.material.material_registry import model_grammar_name
from vimseo.material.material_registry import resolve_material
from vimseo.material_lib import MATERIAL_LIB_DIR


def test_material_lib_directories():
    """Vimseo's own material library is discovered, and comes first."""
    directories = material_lib_directories()
    assert directories[0] == MATERIAL_LIB_DIR
    assert len(set(directories)) == len(directories)


def test_grammar_name_round_trip():
    """A material declares the grammar it conforms to, and the grammar names itself."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
    assert material.grammar_name == "Ta6v"
    assert grammar_name_of(MATERIAL_LIB_DIR / "Ta6v_grammar.json") == "Ta6v"


def test_grammar_name_of_missing_file(tmp_path):
    """An absent or nameless grammar matches no material rather than raising."""
    assert grammar_name_of("") == ""
    assert grammar_name_of(tmp_path / "absent_grammar.json") == ""
    nameless = tmp_path / "nameless_grammar.json"
    nameless.write_text(json.dumps({"properties": {}}))
    assert grammar_name_of(nameless) == ""


def test_generated_grammar_carries_the_name(tmp_path):
    """Regenerating a grammar keeps it bound to the materials pointing at it."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
    schema = material.to_legacy_json_schema(write=True, dir_path=tmp_path)
    assert schema["name"] == "Ta6v"
    assert grammar_name_of(tmp_path / "Ta6v_legacy_grammar.json") == "Ta6v"


def test_model_grammar_and_default_material():
    assert model_grammar_name("BendingTestAnalytical") == "Ta6v"
    assert default_material_name("BendingTestAnalytical") == "Ta6v"


def test_compatible_materials_lists_the_default_first():
    """Every material sharing the model's grammar is offered, its own one first."""
    materials = get_available_materials("BendingTestAnalytical")
    assert [info.name for info in materials] == ["Ta6v", "Ta6v_annealed"]
    assert all(info.grammar_name == "Ta6v" for info in materials)
    assert materials[0].package == "vimseo"


def test_compatible_materials_without_a_material():
    """A model declaring no material offers no choice at all."""
    assert compatible_materials("MockModel") == []


def test_compatible_materials_of_an_unmigrated_model():
    """A model whose material carries no grammar name still offers that one material."""
    assert [info.name for info in compatible_materials("MockModelWithMaterial")] == [
        "MockDefaultMaterial"
    ]


def test_get_available_materials_without_a_model():
    """Without a model name, every discoverable material is returned."""
    names = {info.name for info in get_available_materials()}
    assert {"MockDefaultMaterial", "Ta6v", "Ta6v_annealed"} <= names


def test_resolve_material_by_name_path_and_instance():
    by_name = resolve_material("Ta6v_annealed")
    by_path = resolve_material(MATERIAL_LIB_DIR / "Ta6v_annealed.json")
    assert by_name.name == by_path.name == "Ta6v_annealed"
    assert resolve_material(by_name) is by_name


def test_resolve_unknown_material():
    with pytest.raises(ValueError, match="Unknown material 'NotAMaterial'"):
        resolve_material("NotAMaterial")


def test_create_model_with_a_material():
    """Overriding the material changes the input defaults, never the input names."""
    default = create_model("BendingTestAnalytical", "Cantilever")
    annealed = create_model(
        "BendingTestAnalytical", "Cantilever", material="Ta6v_annealed"
    )
    assert sorted(annealed.input_grammar.names) == sorted(default.input_grammar.names)
    assert annealed.material.name == "Ta6v_annealed"
    assert annealed.default_input_data["young_modulus"] == pytest.approx(200000.0)
    assert default.default_input_data["young_modulus"] == pytest.approx(210000.0)
    # The material reaches the components, not just the model.
    assert annealed._chain.disciplines[0].default_input_data[
        "young_modulus"
    ] == pytest.approx(200000.0)


def test_create_model_with_a_material_instance():
    """An already-built material is used as is, without a library lookup."""
    material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
    material.update_from_dict({"young_modulus": 195000.0})
    model = create_model("BendingTestAnalytical", "Cantilever", material=material)
    assert model.default_input_data["young_modulus"] == pytest.approx(195000.0)
