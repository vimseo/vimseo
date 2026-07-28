<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Integration of models

Integrate the model of interests is the first mandatory step before using the
VV&UQ methods of **VIMSEO**.
As a result, **VIMSEO** should make model integration as easy as possible,
and provide a range of examples to illustrate different ways of integrating models.

**VIMSEO** follows a component-based approach for model integration.
A model contains a list of executable components, which are run sequentially.
To learn more about the advantages of this approach, you can refer to
[model integration explanation](../explanations/model_integration/model_integration.md#a-component-based-model-integration)

## Integration of a **GEMSEO** discipline

```python
--8<-- "src/vimseo/problems/mock/mock_convergence/mock_convergence.py"
```

## Integration of a pure Python model as a single component model

Here, model ``MockModelFields`` defines the variable ``FIELDS_FROM_FILE``,
which means that files corresponding to this pattern are expected to be written
by the model in the scrtch directory.

```python
--8<-- "src/vimseo/problems/mock/mock_fields/mock_fields.py"
```

## Integration of a pure Python model as a pre-run-post component model

```python
--8<-- "src/vimseo/problems/mock/mock_pre_run_post/mock_main.py"
```

And a second example where a material is defined. The input grammar
and default input data are automatically filled with the material properties.

```python
--8<-- "src/vimseo/problems/mock/mock_pre_run_post/mock_with_material.py"
```
