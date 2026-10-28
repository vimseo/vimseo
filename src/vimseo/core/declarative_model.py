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

"""Models wrapping a GEMSEO discipline, declared in YAML files.

A YAML file declares the class attributes of a :class:`.BaseDisciplineModel`:

.. code-block:: yaml

    name: TensileCoupon
    discipline: tensile_coupon:TensileCoupon
    discipline_path: .
    discipline_options: {n_points: 100}
    load_case: Dummy
    summary: A tensile coupon with a bilinear elasto-plastic behaviour.
    material: coupon_material.json
    input_grammar: TensileCoupon_input.json
    plots:
      - [strain_history, stress_history]

The relative paths are relative to the directory of the YAML file.

The models declared in the directories of the ``models_path`` setting
(``VIMSEO_MODELS_PATH``) are registered by :mod:`vimseo.problems.declarative`, so that
they are created by name, as any model. The command ``vimseo_wrap`` writes the JSON input
grammar of a declared model from its discipline, and checks a declaration.
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.utilities.json_grammar_utils import to_json_grammar

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence
    from types import ModuleType

    from gemseo.core.discipline import Discipline

LOGGER = logging.getLogger(__name__)

REGISTRY_MODULE_NAME = "vimseo.problems.declarative"
"""The name of the module whose attributes are the declared models."""


class ModelDeclaration(BaseModel):
    """The declaration of a model wrapping a GEMSEO discipline."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="The name of the model class.")

    discipline: str = Field(
        pattern=r"^[\w.]+:\w+$",
        description="The class of the GEMSEO discipline, as ``module:Class``.",
    )

    discipline_path: Path | None = Field(
        default=None,
        description="A directory added to ``sys.path`` to import the module of the "
        "discipline, when this module is not installed.",
    )

    discipline_options: dict[str, Any] = Field(
        default_factory=dict,
        description="The arguments of the constructor of the discipline.",
    )

    load_case: str = Field(default="Dummy", description="The name of the load case.")

    summary: str = Field(default="", description="A brief description of the model.")

    material: Path | None = Field(
        default=None, description="The path to the material JSON file."
    )

    input_grammar: Path | None = Field(
        default=None,
        description="The path to the JSON grammar file restricting the inputs of the "
        "discipline, e.g. with bounds.",
    )

    plots: list[Annotated[list[str], Field(min_length=2)]] = Field(
        default_factory=list,
        description="The figures, each one as the names of its abscissa and ordinates.",
    )

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> ModelDeclaration:
        """Read a declaration from a YAML file.

        Args:
            file_path: The path to the YAML file.

        Returns:
            The declaration, whose paths are made absolute.

        Raises:
            ValueError: When the declaration is not valid.
        """
        file_path = Path(file_path).resolve()
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        try:
            declaration = cls.model_validate(data)
        except ValidationError as error:
            msg = f"The model declaration {file_path} is not valid: {error}"
            raise ValueError(msg) from None
        for name in ("discipline_path", "material", "input_grammar"):
            path = getattr(declaration, name)
            if path is not None:
                setattr(declaration, name, (file_path.parent / path).resolve())
        return declaration


def create_discipline(declaration: ModelDeclaration) -> Discipline:
    """Import the class of the discipline of a declaration and instantiate it.

    Args:
        declaration: The declaration.

    Returns:
        The discipline.
    """
    if declaration.discipline_path is not None:
        path = str(declaration.discipline_path)
        if path not in sys.path:
            sys.path.insert(0, path)
    module_name, class_name = declaration.discipline.split(":")
    cls = getattr(importlib.import_module(module_name), class_name)
    return cls(**declaration.discipline_options)


def create_model_class(
    declaration: ModelDeclaration, module_name: str
) -> type[BaseDisciplineModel]:
    """Create the class of a declared model.

    Args:
        declaration: The declaration.
        module_name: The name of the module the class belongs to. The model factory
            finds the classes of the modules of VIMSEO and of its plugins; the class is
            to be kept as an attribute of this module, where it is found by its name.

    Returns:
        The class of the model.
    """
    return type(
        declaration.name,
        (BaseDisciplineModel,),
        {
            "__module__": module_name,
            "__doc__": declaration.summary,
            "SUMMARY": declaration.summary,
            "_DISCIPLINE": create_discipline(declaration),
            "_EXPECTED_LOAD_CASE": declaration.load_case,
            "MATERIAL_FILE": declaration.material or "",
            "_INPUT_GRAMMAR_FILE": declaration.input_grammar or "",
            "PLOTS": [tuple(plot) for plot in declaration.plots],
        },
    )


def register_declared_models(
    module: ModuleType, directories: Iterable[str | Path]
) -> list[str]:
    """Create the models declared in the YAML files of directories, as module attributes.

    A declaration which cannot be used is logged and skipped: the model factory ignores
    the errors raised by the modules it imports.

    Args:
        module: The module.
        directories: The directories.

    Returns:
        The names of the registered models.
    """
    names = []
    for directory in directories:
        directory = Path(directory)
        if not directory.is_dir():
            LOGGER.warning("The models path %s is not a directory.", directory)
            continue
        for file_path in sorted(directory.glob("*.yaml")):
            try:
                declaration = ModelDeclaration.from_yaml(file_path)
                if declaration.name in names:
                    msg = f"The model {declaration.name} is already declared."
                    raise ValueError(msg)  # ruff: ignore[raise-within-try]
                cls = create_model_class(declaration, module.__name__)
            except Exception:  # ruff: ignore[blind-except] - one bad file must not hide the others
                LOGGER.exception("The model declared in %s is ignored.", file_path)
                continue
            setattr(module, cls.__name__, cls)
            names.append(cls.__name__)
    return names


def write_input_grammar(file_path: str | Path, force: bool = False) -> Path:
    """Write the input grammar of a declared model, from its discipline, as a JSON file.

    The file is to be completed, e.g. with the bounds of some inputs, and referenced in
    the YAML file by ``input_grammar``.

    Args:
        file_path: The path to the YAML file declaring the model.
        force: Whether to overwrite an existing JSON file.

    Returns:
        The path to the JSON file: ``input_grammar`` when declared, otherwise
        ``{name}_input.json`` next to the YAML file.

    Raises:
        FileExistsError: When the JSON file exists and ``force`` is ``False``.
    """
    declaration = ModelDeclaration.from_yaml(file_path)
    json_path = (
        declaration.input_grammar
        or Path(file_path).resolve().parent / f"{declaration.name}_input.json"
    )
    if json_path.exists() and not force:
        msg = f"The file {json_path} exists; use force to overwrite it."
        raise FileExistsError(msg)
    schema = to_json_grammar(create_discipline(declaration).input_grammar).schema
    properties = schema["properties"]
    for prop in properties.values():
        prop.setdefault("description", "")
    json_path.write_text(
        json.dumps(
            {"$schema": schema["$schema"], "type": "object", "properties": properties},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return json_path


def _check(file_path: Path) -> None:
    """Create a declared model and print its description and its input bounds.

    Args:
        file_path: The path to the YAML file declaring the model.
    """
    from vimseo.core.model_factory import ModelFactory

    declaration = ModelDeclaration.from_yaml(file_path)
    # Queried before creating the class below, which the factory would find too.
    factory = ModelFactory()
    if not factory.is_available(declaration.name):
        print(
            f"The model {declaration.name} is not available to create_model: add the "
            f"directory {file_path.resolve().parent} to VIMSEO_MODELS_PATH."
        )
    elif (module_name := factory.get_class(declaration.name).__module__) != (
        REGISTRY_MODULE_NAME
    ):
        print(
            f"The name {declaration.name} is already the one of a model of "
            f"{module_name}: rename the declared model."
        )

    # A module name out of VIMSEO, so that the model factory ignores this class.
    cls = create_model_class(declaration, "__main__")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        model = cls(
            declaration.load_case,
            directory_archive_root=Path(directory) / "archive",
            directory_scratch_root=Path(directory) / "scratch",
            cache_file_path=Path(directory) / "cache.hdf",
        )
        print(model.description)
        print(f"Lower bounds: {model.lower_bounds}")
        print(f"Upper bounds: {model.upper_bounds}")


def main(argv: Sequence[str] | None = None) -> None:
    """Run the command ``vimseo_wrap``.

    Args:
        argv: The command line arguments. By default, those of ``sys.argv``.
    """
    parser = argparse.ArgumentParser(
        prog="vimseo_wrap",
        description="Wrap a GEMSEO discipline as a VIMSEO model declared in a YAML "
        "file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    write_parser = subparsers.add_parser(
        "write-grammar",
        help="Write the JSON input grammar of the model from its discipline, "
        "to be completed with bounds.",
    )
    write_parser.add_argument("yaml_file", type=Path)
    write_parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing JSON file."
    )
    check_parser = subparsers.add_parser(
        "check", help="Create the model and print its description and input bounds."
    )
    check_parser.add_argument("yaml_file", type=Path)
    args = parser.parse_args(argv)

    if args.command == "write-grammar":
        json_path = write_input_grammar(args.yaml_file, args.force)
        print(f"The input grammar of the discipline is written in {json_path}.")
        print(
            "Bound inputs with 'minimum' and 'maximum' in their 'items', remove the "
            "inputs not to restrict, and reference the file in the YAML file with "
            f"'input_grammar: {json_path.name}'."
        )
    else:
        _check(args.yaml_file)


if __name__ == "__main__":
    main()
