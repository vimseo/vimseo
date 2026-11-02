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
from vimseo.core.model_settings import IntegratedModelSettings

MODELS_DIR = Path("declarative_models")
RUNS_DIR = EXAMPLE_RUNS_DIR / "declarative_model"


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
# The declaration is read from the YAML file, and the class of the model is created
# from it. In normal use, the model is rather created by its name (see the last
# section).

declaration = ModelDeclaration.from_yaml(MODELS_DIR / "Rectangle.yaml")
model = create_declared_model(declaration)
print(model.description)
model.execute()
print(model.get_output_data()["area"])

# %%
# Bound the inputs with a JSON grammar
# ------------------------------------
#
# The discipline ``Rectangle`` has a ``SimpleGrammar``, which gives the types of its
# inputs but no bounds. The JSON grammar file declared by ``input_grammar`` replaces
# the input grammar of the discipline, here to bound its inputs. The command
# ``vimseo_wrap write-grammar Rectangle.yaml`` writes this file from the discipline,
# with the types of all its inputs; the ``minimum`` and ``maximum`` of the ``items``
# of the inputs to bound are then added by hand:

print((MODELS_DIR / "Rectangle_input.json").read_text())

# %%
# The model bounds are read from this grammar:

print(model.lower_bounds)
print(model.upper_bounds)

# %%
# and an input out of these bounds makes the simulation fail:

try:
    model.execute({"width": array([20.0])})
except InvalidDataError as error:
    print(error)

# %%
# The discipline still validates its inputs with its own grammar after the model, so
# the file declares all the inputs of the discipline and can only restrict them: a
# missing input, a variable unknown to the discipline, a different type or a looser
# bound raises a ``ValueError`` when the model is created. For instance, without the
# input ``height``:

grammar = json.loads((MODELS_DIR / "Rectangle_input.json").read_text())
del grammar["properties"]["height"]
RUNS_DIR.mkdir(parents=True, exist_ok=True)
incomplete_grammar_path = RUNS_DIR / "Rectangle_incomplete_input.json"
incomplete_grammar_path.write_text(json.dumps(grammar))
try:
    create_declared_model(
        declaration.model_copy(update={"input_grammar": incomplete_grammar_path})
    )
except ValueError as error:
    print(error)

# %%
# Discipline options, material and figures
# ----------------------------------------
#
# The discipline ``CantileverBeam`` computes the deflection of a cantilever beam under
# a tip load. Its grammar is built from its default values, so it has no bounds either.
# The declaration passes an option to the constructor of the discipline, gives a
# material, and declares a figure, as the names of its abscissa and ordinates:

print((MODELS_DIR / "Beam.yaml").read_text())

# %%
# The properties of the material are named after inputs of the discipline. Its values
# are the default values of these inputs, which are classified as material variables:

print((MODELS_DIR / "steel.json").read_text())
model = create_declared_model(ModelDeclaration.from_yaml(MODELS_DIR / "Beam.yaml"))
print(model.description)

# %%
# The bounds of the material properties shall be within those of the input grammar.
# Its stochastic properties define an uncertain space:

print(model.material.to_parameter_space())

# %%
# The results are visualised with the figures declared by ``plots``:

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
