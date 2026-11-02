# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This work is licensed under a BSD 0-Clause License.
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
# FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Declare a model wrapping a GEMSEO discipline in a YAML file
===========================================================

The example ``plot_05_discipline_with_material`` wraps a GEMSEO discipline by deriving a
class from ``BaseDisciplineModel`` in Python. The same can be done without writing
Python nor installing code, by declaring the model in a YAML file. Each key of the YAML
file sets a class attribute of a ``BaseDisciplineModel``; only ``name`` and
``discipline`` are required, and the relative paths are relative to the YAML file.

The YAML and JSON files of this example are in the directory ``declarative_models``,
with the module ``wrapping_disciplines`` defining the GEMSEO disciplines.
"""

# %%
from __future__ import annotations

import json
from pathlib import Path

from gemseo.core.grammars.errors import InvalidDataError
from numpy import array

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.core.declarative_model import ModelDeclaration
from vimseo.core.declarative_model import create_model_class
from vimseo.core.declarative_model import main as vimseo_wrap
from vimseo.core.model_settings import IntegratedModelSettings

MODELS_DIR = Path("declarative_models")
RUNS_DIR = EXAMPLE_RUNS_DIR / "declarative_model"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# %%
# In normal use, a declared model is created by its name with ``create_model``, as any
# VIMSEO model, once the directory of its YAML file is in the environment variable
# ``VIMSEO_MODELS_PATH`` (see the last section). This example rather uses the helper
# below, only so that it runs as is: the helper creates the class of the model from
# its YAML file, without setting ``VIMSEO_MODELS_PATH``, and stores the archive, the
# scratch and the cache of the model in the directory of the runs of the example.
# It is not meant to be reused in your own scripts.


def create_declared_model(declaration: ModelDeclaration):
    """Create a declared model, keeping its archive, scratch and cache in RUNS_DIR."""
    settings = IntegratedModelSettings(
        directory_archive_root=RUNS_DIR / "archive",
        directory_scratch_root=RUNS_DIR / "scratch",
        cache_file_path=RUNS_DIR / "caches" / f"{declaration.name}.hdf",
    )
    cls = create_model_class(declaration, "__main__")
    return cls(declaration.load_case, **settings.model_dump())


# %%
# A first declared model
# ----------------------
#
# The discipline ``Rectangle`` computes the area and the perimeter of a rectangle. It
# is declared by the name of its class, as ``module:Class``, and by the directory of
# its module, which is not installed:

print((MODELS_DIR / "Rectangle.yaml").read_text())

# %%
# The declaration is read from the YAML file, and the model is created from it:

model = create_declared_model(ModelDeclaration.from_yaml(MODELS_DIR / "Rectangle.yaml"))
print(model.description)
model.execute()
print(model.get_output_data()["area"])

# %%
# The discipline ``Rectangle`` has a ``SimpleGrammar``, which gives the types of its
# inputs but no bounds, so the inputs of the model are not bounded:

print(model.lower_bounds)
print(model.upper_bounds)

# %%
# Bound the inputs with a JSON grammar
# ------------------------------------
#
# The discipline ``CantileverBeam`` computes the deflection of a cantilever beam under
# a tip load. Its ``JSONGrammar`` is built from its default values, so it gives the
# types of its inputs but no bounds either. The JSON grammar file declared by
# ``input_grammar`` replaces the input grammar of the discipline, here to bound its
# inputs. Here is the YAML file of the model, which also declares an option of the
# constructor of the discipline, a material and a figure, presented in the next
# section:

print((MODELS_DIR / "Beam.yaml").read_text())

# %%
# The JSON grammar file is written in three steps.
#
# 1. Write the grammar of the discipline with the command
#    ``vimseo_wrap write-grammar Beam.yaml``. It writes the file declared by
#    ``input_grammar``, or ``{name}_input.json`` next to the YAML file when this key is
#    missing, as here, where the model is first declared without ``input_grammar``:

draft_yaml_path = RUNS_DIR / "Beam.yaml"
draft_yaml_path.write_text(
    "name: DeclaredBeam\n"
    "discipline: wrapping_disciplines:CantileverBeam\n"
    f"discipline_path: {MODELS_DIR.resolve().as_posix()}\n"
)
vimseo_wrap(["write-grammar", str(draft_yaml_path), "--force"])

# %%
#    The file declares all the inputs of the discipline with their types, and an empty
#    description:

print((RUNS_DIR / "DeclaredBeam_input.json").read_text())

# %%
# 2. Add the bounds by hand, with the keys ``minimum`` and ``maximum``, and optionally
#    a description. An input of a GEMSEO discipline is a NumPy array, so its property
#    in the grammar is of type ``array``: the bounds apply to its components, and are
#    thus set in the block ``items`` describing them, beside their
#    ``"type": "number"``, not at the level of the property itself:
#
#    .. code-block:: json
#
#        "force": {
#          "type": "array",
#          "items": {
#            "type": "number",
#            "minimum": 0.0,
#            "maximum": 5000.0
#          },
#          "description": "The tip load [N]."
#        }
#
#    A ``minimum`` or a ``maximum`` set beside ``"type": "array"`` would not bound the
#    values and would be ignored by VIMSEO. Here is the completed file:

print((MODELS_DIR / "Beam_input.json").read_text())

# %%
# 3. Reference the file in the YAML file, with ``input_grammar: Beam_input.json``.
#
# The model bounds are then read from this grammar:

model = create_declared_model(ModelDeclaration.from_yaml(MODELS_DIR / "Beam.yaml"))
print(model.lower_bounds)
print(model.upper_bounds)

# %%
# and an input out of these bounds makes the simulation fail:

try:
    model.execute({"force": array([10000.0])})
except InvalidDataError as error:
    print(error)

# %%
# The discipline still validates its inputs with its own grammar after the model, so
# the file declares all the inputs of the discipline and can only restrict them: a
# missing input, a variable unknown to the discipline, a different type or a looser
# bound raises a ``ValueError`` when the model is created. For instance, without the
# input ``height``:

grammar = json.loads((MODELS_DIR / "Beam_input.json").read_text())
del grammar["properties"]["height"]
incomplete_grammar_path = RUNS_DIR / "Beam_incomplete_input.json"
incomplete_grammar_path.write_text(json.dumps(grammar))
declaration = ModelDeclaration.from_yaml(MODELS_DIR / "Beam.yaml")
try:
    create_declared_model(
        declaration.model_copy(update={"input_grammar": incomplete_grammar_path})
    )
except ValueError as error:
    print(error)

# %%
# Material and figures
# --------------------
#
# The material declared by ``material`` is a JSON file, whose format is described in
# [Material file format](../../../references/materials/material_file_format.md).
# The properties of the material are named after inputs of the discipline. Their
# values are the default values of these inputs, which are classified as material
# variables:

print((MODELS_DIR / "steel.json").read_text())
print(model.description)

# %%
# The bounds of the material properties shall be within those of the input grammar,
# which is checked when the model is created. The stochastic properties of the
# material define an uncertain space:

print(model.material.to_parameter_space())

# %%
# The results are visualised with the figures declared by ``plots``, each one given
# by the names of its abscissa and ordinates:

model.execute()
print(model.get_output_data()["tip_deflection"])
figures = model.plot_results(show=True)

# %%
# A discipline bounding its own inputs
# ------------------------------------
#
# The discipline ``BoundedCantileverBeam`` reads its input grammar from a JSON file
# with bounds. Without ``input_grammar``, the model bounds are those of the
# discipline:

print((MODELS_DIR / "BoundedBeam.yaml").read_text())
model = create_declared_model(
    ModelDeclaration.from_yaml(MODELS_DIR / "BoundedBeam.yaml")
)
print(model.lower_bounds)
print(model.upper_bounds)

# %%
# A model without any Python
# --------------------------
#
# A discipline of an installed package needs no ``discipline_path``. The
# ``AnalyticDiscipline`` of GEMSEO computes outputs from expressions, given as an
# option of its constructor:

print((MODELS_DIR / "Analytic.yaml").read_text())
model = create_declared_model(ModelDeclaration.from_yaml(MODELS_DIR / "Analytic.yaml"))
model.execute({"a": array([1.0]), "b": array([3.0]), "x": array([2.0])})
print(model.get_output_data()["y"], model.get_output_data()["z"])

# %%
# Use the declared models by their names
# --------------------------------------
#
# The YAML files of the directories of the environment variable
# ``VIMSEO_MODELS_PATH`` are registered when VIMSEO is imported, so that the declared
# models are created by their names, as any VIMSEO model, and can be used by any
# tool. The directories are separated by ``;`` on Windows and ``:`` otherwise:
#
# .. code-block:: console
#
#     export VIMSEO_MODELS_PATH=/path/to/declarative_models
#
# .. code-block:: python
#
#     from vimseo.api import create_model
#
#     if __name__ == "__main__":
#         model = create_model("DeclaredBeam", "Dummy")
#         model.execute()
#
# On Windows, the ``if __name__ == "__main__":`` guard is required in a script
# executing a model: the HDF5 cache of the model starts a process which re-imports the
# script.
#
# The command ``vimseo_wrap check Beam.yaml`` creates the model, prints its
# description and its input bounds, and tells whether ``create_model`` finds it.
