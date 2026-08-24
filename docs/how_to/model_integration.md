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

If you have a model defined as a Python code, the integration process to **VIMSEO** can be:

- wrap this model in a **GEMSEO** discipline
- use the above procedure to convert it as a **VIMSEO** model

## Integration of a pure Python model as a pre-run-post component model

If you have a model defined from Python code, and want to integrate it as a three-step pre-processing, run-processing and post-processing:

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
