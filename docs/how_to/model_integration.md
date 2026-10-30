<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Integration of models

Integrate the models of interest is the first mandatory step before using the
VV&UQ methods of **VIMSEO**.
As a result, **VIMSEO** should make model integration as easy as possible,
and provide a range of examples to illustrate different ways of integrating models.

**VIMSEO** follows a component-based approach for model integration.
A model contains a list of executable components, which are run sequentially.
To learn more about the advantages of this approach, you can refer to
[model integration explanation](../explanations/model_integration/model_integration.md#a-component-based-model-integration)

## Integration of a **GEMSEO** discipline

A **GEMSEO** discipline can be easily turned into a **VIMSEO** model,
by deriving a class from `BaseDisciplineModel` and setting the `_DISCIPLINE`
class attribute:

```python
--8<-- "src/vimseo/problems/mock/mock_convergence/mock_convergence.py"
```

The cache of the discipline is disabled: the model manages the cache.

A material is declared with the `MATERIAL_FILE` class attribute, or passed to the
constructor (`material=...`, also through `create_model`). Its property values become the
default values of the discipline inputs of the same names; each property must be an
input of the discipline.

The inputs can be bounded by a JSON grammar file, declared with the
`_INPUT_GRAMMAR_FILE` class attribute. This file replaces the input grammar of the
discipline: the component wrapping the discipline gets its JSON grammar, e.g. with the
`minimum` and `maximum` of the `items` of an input. The model input bounds are read
from this grammar, and an input out of these bounds makes the simulation fail. The
discipline still validates its inputs with its own grammar, so the file declares all
the inputs of the discipline and can only restrict them: a variable unknown to the
discipline, a missing input, a different type or a looser bound raises an error.

If you have a model implemented in a Python script, you may integrate the process to **VIMSEO** by:

- wrapping this model in a **GEMSEO** discipline
- using the above procedure to convert it as a **VIMSEO** model

## Declarative integration of a **GEMSEO** discipline

A **GEMSEO** discipline can also be turned into a **VIMSEO** model without writing
Python, by declaring the model in a YAML file:

```yaml
name: TensileCoupon                       # the name of the model
discipline: tensile_coupon:TensileCoupon  # the discipline class, as module:Class
discipline_path: .                        # the directory of the module, if not installed
discipline_options: {n_points: 100}       # the arguments of the discipline constructor
load_case: Dummy                          # the load case, Dummy by default
summary: A tensile coupon with a bilinear elasto-plastic behaviour.
material: coupon_material.json            # the material JSON file
input_grammar: TensileCoupon_input.json   # the JSON grammar file replacing the discipline one
plots:                                    # the figures: abscissa, then ordinates
  - [strain_history, stress_history]
```

The relative paths are relative to the directory of the YAML file. Each key sets a
class attribute of a `BaseDisciplineModel`: only `name` and `discipline` are required.

The command `vimseo_wrap` helps to write the declaration:

- `vimseo_wrap write-grammar TensileCoupon.yaml` writes the input grammar of the
  discipline as a JSON file, with the types of the inputs. Complete it with the
  `minimum` and `maximum` of the `items` of the inputs to bound, keeping all the inputs,
  and reference the file in the YAML file with `input_grammar`.
- `vimseo_wrap check TensileCoupon.yaml` creates the model and prints its description
  and its input bounds; it also tells whether `create_model` finds the model.

The models declared in the directories of the environment variable `VIMSEO_MODELS_PATH`
(separated by `;` on Windows, `:` otherwise) are available by their name, as any model:

```python
from vimseo.api import create_model

model = create_model("TensileCoupon", "Dummy")
```

No development installation is needed: the discipline module is imported from
`discipline_path` when it is not installed.

## Integration of a pure Python model as a pre-run-post component model

If you have a model implemented in a Python script, and want to integrate it as a three-step pre-processing, run-processing and post-processing:

```python
--8<-- "src/vimseo/problems/mock/mock_pre_run_post/mock_main.py"
```

```python
--8<-- "src/vimseo/problems/mock/mock_pre_run_post/mock_components_lc1.py"
```

If you also want to define a material for this model, you can look at the below example:

```python
--8<-- "src/vimseo/problems/mock/mock_pre_run_post/mock_with_material.py"
```

<!--
It is weird that we talk about material grammar without before mentionning model/components grammar.
-->

The material itself is defined from two files. Its grammar, possibly defining the bounds and types of the properties:

```python
--8<-- "src/vimseo/material_lib/Mock_grammar.json"
```

and the values, possibly defining probability distributions for the properties:

```python
--8<-- "src/vimseo/material_lib/Mock.json"
```

The input grammar and default input data are automatically filled with the material properties.
