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
import os
import re
import subprocess
import sys
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
import yaml
from numpy import array

from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.core.declarative_model import ModelDeclaration
from vimseo.core.declarative_model import create_model_class
from vimseo.core.declarative_model import main
from vimseo.core.declarative_model import register_declared_models
from vimseo.core.declarative_model import write_input_grammar
from vimseo.material.material import Material
from vimseo.material.material_property import MaterialProperty
from vimseo.material.material_relation import MaterialRelation

if TYPE_CHECKING:
    from pathlib import Path

# A module name out of VIMSEO, so that the model factory ignores the test classes.
MODULE_NAME = "declared_models_for_tests"

DECLARATION = {
    "name": "DeclaredStiffness",
    "discipline": "gemseo.disciplines.analytic:AnalyticDiscipline",
    "discipline_options": {"expressions": {"stiffness": "modulus*area"}},
    "summary": "A stiffness.",
    "material": "material.json",
    "plots": [["modulus", "stiffness"]],
}


def _write_declaration(directory: Path, **changes) -> Path:
    """Write a declaration and its material in a directory."""
    material = Material(
        name="TestMaterial",
        material_relations=[
            MaterialRelation(
                name="Elastic",
                properties=[MaterialProperty(name="modulus", value=150000.0)],
            )
        ],
    )
    (directory / "material.json").write_text(
        material.model_dump_json(), encoding="utf-8"
    )
    declaration = {**DECLARATION, **changes}
    file_path = directory / f"{declaration['name']}.yaml"
    file_path.write_text(yaml.safe_dump(declaration), encoding="utf-8")
    return file_path


def test_from_yaml_resolves_the_paths(tmp_path):
    """The relative paths are relative to the directory of the YAML file."""
    file_path = _write_declaration(
        tmp_path,
        discipline_path="disciplines",
        material="mat.json",
        input_grammar="../grammar.json",
    )

    declaration = ModelDeclaration.from_yaml(file_path)

    assert declaration.discipline_path == tmp_path.resolve() / "disciplines"
    assert declaration.material == tmp_path.resolve() / "mat.json"
    assert declaration.input_grammar == tmp_path.resolve().parent / "grammar.json"
    assert declaration.load_case == "Dummy"


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"unknown": 1}, "unknown"),
        ({"discipline": "no_class"}, "discipline"),
        ({"plots": [["x"]]}, "plots.0"),
    ],
)
def test_from_yaml_invalid(tmp_path, changes, field):
    """An invalid declaration raises an error naming the file and the field."""
    file_path = _write_declaration(tmp_path, **changes)

    with pytest.raises(
        ValueError,
        match=re.escape(f"The model declaration {file_path} is not valid")
        + f"(.|\\n)*{re.escape(field)}",
    ):
        ModelDeclaration.from_yaml(file_path)


def test_create_model_class(tmp_wd):
    """The declaration sets the class attributes, and the model uses the material."""
    declaration = ModelDeclaration.from_yaml(_write_declaration(tmp_wd))

    cls = create_model_class(declaration, MODULE_NAME)

    assert issubclass(cls, BaseDisciplineModel)
    assert cls.__name__ == "DeclaredStiffness"
    assert cls.__module__ == MODULE_NAME
    assert cls.SUMMARY == "A stiffness."
    assert cls.PLOTS == [("modulus", "stiffness")]
    assert cls._EXPECTED_LOAD_CASE == "Dummy"
    assert cls._INPUT_GRAMMAR_FILE == ""
    model = cls("Dummy")
    output_data = model.execute({"area": array([2.0])})
    assert output_data["stiffness"][0] == 300000.0  # ruff: ignore[float-equality-comparison]


def test_discipline_path(tmp_wd):
    """The module of the discipline is imported from ``discipline_path``."""
    module_name = "declared_discipline_for_tests"
    (tmp_wd / "disciplines").mkdir()
    (tmp_wd / "disciplines" / f"{module_name}.py").write_text(
        "from gemseo.disciplines.analytic import AnalyticDiscipline\n\n\n"
        "class Doubler(AnalyticDiscipline):\n"
        "    def __init__(self):\n"
        "        super().__init__({'y': '2*x'})\n",
        encoding="utf-8",
    )
    declaration = ModelDeclaration.from_yaml(
        _write_declaration(
            tmp_wd,
            discipline=f"{module_name}:Doubler",
            discipline_path="disciplines",
            discipline_options={},
            material=None,
            plots=[],
        )
    )
    sys_path = list(sys.path)
    try:
        model = create_model_class(declaration, MODULE_NAME)("Dummy")
        assert model.execute({"x": array([3.0])})["y"][0] == 6.0  # ruff: ignore[float-equality-comparison]
    finally:
        sys.path[:] = sys_path
        sys.modules.pop(module_name, None)


def test_write_input_grammar(tmp_wd):
    """The JSON input grammar is written from the discipline, but not overwritten."""
    file_path = _write_declaration(tmp_wd)

    json_path = write_input_grammar(file_path)

    assert json_path == tmp_wd.resolve() / "DeclaredStiffness_input.json"
    properties = json.loads(json_path.read_text(encoding="utf-8"))["properties"]
    assert properties == {
        name: {"type": "array", "items": {"type": "number"}, "description": ""}
        for name in ("modulus", "area")
    }
    with pytest.raises(FileExistsError, match="use force to overwrite it"):
        write_input_grammar(file_path)
    write_input_grammar(file_path, force=True)


def test_model_with_input_grammar(tmp_wd):
    """The JSON input grammar, completed with bounds, bounds the model inputs."""
    file_path = _write_declaration(tmp_wd, input_grammar="grammar.json")
    json_path = write_input_grammar(file_path)
    schema = json.loads(json_path.read_text(encoding="utf-8"))
    schema["properties"]["area"]["items"].update(minimum=1.0, maximum=3.0)
    del schema["properties"]["modulus"]
    json_path.write_text(json.dumps(schema), encoding="utf-8")

    model = create_model_class(ModelDeclaration.from_yaml(file_path), MODULE_NAME)(
        "Dummy"
    )

    assert model.lower_bounds == {"area": 1.0}
    assert model.upper_bounds == {"area": 3.0}


def test_register_declared_models(tmp_wd, caplog):
    """The valid declarations become module attributes; the others are logged."""
    _write_declaration(tmp_wd)
    _write_declaration(tmp_wd, name="Duplicate")
    (tmp_wd / "Duplicate.yaml").rename(tmp_wd / "zz_duplicate.yaml")
    duplicate = yaml.safe_load((tmp_wd / "zz_duplicate.yaml").read_text())
    duplicate["name"] = "DeclaredStiffness"
    (tmp_wd / "zz_duplicate.yaml").write_text(yaml.safe_dump(duplicate))
    (tmp_wd / "invalid.yaml").write_text("name: Invalid\n")
    module = ModuleType(MODULE_NAME)

    names = register_declared_models(module, [tmp_wd, tmp_wd / "missing"])

    assert names == ["DeclaredStiffness"]
    assert module.DeclaredStiffness.__module__ == MODULE_NAME
    assert "is not a directory" in caplog.text
    assert f"The model declared in {tmp_wd / 'invalid.yaml'} is ignored" in caplog.text
    assert "The model DeclaredStiffness is already declared" in caplog.text


def test_main_write_grammar_and_check(tmp_wd, capsys):
    """The command writes the input grammar and prints the model description."""
    file_path = _write_declaration(tmp_wd)

    main(["write-grammar", str(file_path)])
    assert "input_grammar: DeclaredStiffness_input.json" in capsys.readouterr().out

    main(["check", str(file_path)])
    out = capsys.readouterr().out
    assert "is not available to create_model" in out
    assert "Model DeclaredStiffness: A stiffness." in out
    assert "Lower bounds:" in out


def test_models_path(tmp_wd):
    """The models of ``VIMSEO_MODELS_PATH`` are created by name, and a model pickled in
    a process is loaded in another one."""
    _write_declaration(tmp_wd)
    env = {**os.environ, "VIMSEO_MODELS_PATH": str(tmp_wd)}

    def run(script):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp_wd,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.split()[-1]

    module_name = run(
        "import pickle\n"
        "from pathlib import Path\n"
        "from vimseo.api import create_model\n"
        "if __name__ == '__main__':\n"
        "    model = create_model('DeclaredStiffness', 'Dummy')\n"
        "    Path('model.pkl').write_bytes(pickle.dumps(model))\n"
        "    print(type(model).__module__)\n"
    )
    stiffness = run(
        "import pickle\n"
        "from pathlib import Path\n"
        "from numpy import array\n"
        "if __name__ == '__main__':\n"
        "    model = pickle.loads(Path('model.pkl').read_bytes())\n"
        "    print(model.execute({'area': array([2.0])})['stiffness'][0])\n"
    )

    assert module_name == "vimseo.problems.declarative"
    assert stiffness == "300000.0"
