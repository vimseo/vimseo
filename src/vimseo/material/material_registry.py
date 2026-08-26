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

"""Discovery of the materials shipped by |v| and its plugins.

Materials live as ``{Name}.json`` / ``{Name}_grammar.json`` pairs inside a
``material_lib`` sub-package -- |v|'s own, plus one per installed plugin. A model
binds one of them through :attr:`~.IntegratedModel.MATERIAL_FILE` and the grammar it
must satisfy through :attr:`~.IntegratedModel._MATERIAL_GRAMMAR_FILE`.

This module answers the question the model class alone cannot: *which other materials
could this model use instead?* The link is declarative -- a material's
:attr:`~.Material.grammar_name` names the grammar it conforms to, and a grammar names
itself through its own ``name`` field -- so a material is compatible with a model when
those two names match. No structural comparison of property names is attempted: the
declaration is the contract.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING

from vimseo.material.material import Material

if TYPE_CHECKING:
    from collections.abc import Iterator

LOGGER = logging.getLogger(__name__)

MATERIAL_LIB_PACKAGE = "material_lib"
"""The sub-package a plugin ships its materials in."""

PLUGIN_ENTRY_POINT = "gemseo_plugins"
"""The entry-point group |v| and its plugins register themselves under.

The same one :class:`gemseo.core.base_factory.BaseFactory` uses to discover plugin
classes, so a plugin whose models are visible is a plugin whose materials are too.
"""

GRAMMAR_FILE_SUFFIX = "_grammar.json"
"""The suffix telling a grammar file apart from a material values file."""


@dataclass(frozen=True)
class MaterialInfo:
    """A material found in a ``material_lib``, without loading its properties."""

    name: str
    """The material name, i.e. the identifier accepted by :func:`~vimseo.api.create_model`."""

    grammar_name: str = ""
    """The name of the grammar this material declares conformance to."""

    file_path: Path | None = None
    """The path to the material JSON file."""

    package: str = ""
    """The package shipping it, e.g. ``"vimseo"`` or ``"vimseo_composites"``."""

    description: str = ""
    """The material description, for display."""


_MATERIALS_CACHE: list[MaterialInfo] | None = None


def material_lib_directories() -> list[Path]:
    """Return every installed ``<plugin>.material_lib`` directory.

    |v|'s own comes first, since |v| registers itself under the plugin entry point
    before any plugin can. A plugin that ships no ``material_lib`` is skipped.
    """
    directories: list[Path] = []
    for entry_point in entry_points(group=PLUGIN_ENTRY_POINT):
        module_name = f"{entry_point.value}.{MATERIAL_LIB_PACKAGE}"
        try:
            module = import_module(module_name)
        except ImportError:
            continue
        path = getattr(module, "__path__", None)
        if not path:
            continue
        directory = Path(path[0]).resolve()
        if directory not in directories:
            directories.append(directory)
    return directories


def _package_of(directory: Path) -> str:
    """Return the top-level package name a ``material_lib`` directory belongs to."""
    return directory.parent.name


def iter_materials() -> Iterator[MaterialInfo]:
    """Yield every material found across the installed ``material_lib`` directories.

    Grammar files are skipped, and a file that is not a readable material is logged and
    skipped rather than aborting the whole scan -- one malformed JSON in one plugin must
    not make every other material unreachable.
    """
    for directory in material_lib_directories():
        package = _package_of(directory)
        for file_path in sorted(directory.glob("*.json")):
            if file_path.name.endswith(GRAMMAR_FILE_SUFFIX):
                continue
            try:
                data = json.loads(file_path.read_text())
                name = data["name"]
            except Exception:  # noqa: BLE001 - one bad file must not hide the others
                LOGGER.warning("Skipping unreadable material file %s.", file_path)
                continue
            yield MaterialInfo(
                name=name,
                grammar_name=data.get("grammar_name", ""),
                file_path=file_path,
                package=package,
                description=data.get("description", ""),
            )


def available_materials(refresh: bool = False) -> list[MaterialInfo]:
    """Return every discoverable material.

    The scan reads one JSON file per material, so its result is memoized: the callers
    are long-lived processes (the |v| worker behind the GUI) asking for this list on
    every model change. Pass ``refresh=True`` after adding a material file at runtime.
    """
    global _MATERIALS_CACHE  # noqa: PLW0603
    if refresh or _MATERIALS_CACHE is None:
        _MATERIALS_CACHE = list(iter_materials())
    return list(_MATERIALS_CACHE)


def grammar_name_of(grammar_file: Path | str) -> str:
    """Return the ``name`` declared by a material grammar file.

    Returns an empty string when the file is missing, unreadable, or declares no name --
    an unnamed grammar simply matches no material.
    """
    if not grammar_file:
        return ""
    try:
        return json.loads(Path(grammar_file).read_text()).get("name", "")
    except Exception:  # noqa: BLE001
        LOGGER.warning("Cannot read the material grammar %s.", grammar_file)
        return ""


def _model_class(model_name: str):
    from vimseo.core.model_factory import ModelFactory

    return ModelFactory().get_class(model_name)


def model_grammar_name(model_name: str) -> str:
    """Return the name of the material grammar a model requires ("" if it has none)."""
    return grammar_name_of(
        getattr(_model_class(model_name), "_MATERIAL_GRAMMAR_FILE", "")
    )


def default_material_name(model_name: str) -> str:
    """Return the name of the material a model binds by default ("" if it binds none)."""
    material_file = getattr(_model_class(model_name), "MATERIAL_FILE", "")
    if not material_file:
        return ""
    try:
        return json.loads(Path(material_file).read_text())["name"]
    except Exception:  # noqa: BLE001
        LOGGER.warning("Cannot read the material file %s.", material_file)
        return ""


def compatible_materials(model_name: str) -> list[MaterialInfo]:
    """Return the materials a model can be built with, its own default first.

    Empty for a model declaring no :attr:`~.IntegratedModel.MATERIAL_FILE` -- such a
    model has no material to choose. The default is always listed even when its JSON
    carries no :attr:`~.Material.grammar_name` yet, so a model whose material library has
    not been migrated keeps working with exactly the one material it always had.
    """
    default_name = default_material_name(model_name)
    if not default_name:
        return []
    grammar_name = model_grammar_name(model_name)
    default: MaterialInfo | None = None
    others: list[MaterialInfo] = []
    for info in available_materials():
        if info.name == default_name:
            default = info
        elif grammar_name and info.grammar_name == grammar_name:
            others.append(info)
    if default is None:
        # Declared through a path outside any material_lib; still offer it.
        default = MaterialInfo(name=default_name, grammar_name=grammar_name)
    return [default, *others]


def find_material(name: str) -> MaterialInfo:
    """Return the discoverable material called *name*.

    Raises:
        ValueError: If no material has this name, or if more than one package ships a
            material with it -- picking one silently would make the model built depend
            on which plugins happen to be installed.
    """
    matches = [info for info in available_materials() if info.name == name]
    if not matches:
        known = ", ".join(sorted({info.name for info in available_materials()}))
        msg = f"Unknown material {name!r}. Available materials: {known}."
        raise ValueError(msg)
    if len(matches) > 1:
        packages = ", ".join(sorted(info.package for info in matches))
        msg = (
            f"The material name {name!r} is ambiguous: it is shipped by {packages}. "
            f"Pass the path to the material file instead."
        )
        raise ValueError(msg)
    return matches[0]


def resolve_material(material: str | Path | Material) -> Material:
    """Return a :class:`.Material` from a name, a JSON file path, or an instance.

    A :class:`.Material` is returned as is; a :class:`~pathlib.Path` (or a string naming
    an existing file) is read directly; anything else is looked up by name across the
    installed material libraries.
    """
    if isinstance(material, Material):
        return material
    if isinstance(material, Path) or Path(material).is_file():
        return Material.from_json(Path(material))
    return Material.from_json(find_material(str(material)).file_path)
