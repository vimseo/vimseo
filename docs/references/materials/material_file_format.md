<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Material file format

A material card is a JSON file giving the values of the material properties of a
model, with their bounds and, optionally, their probability distributions. It is read
into a `vimseo.material.material.Material`.

A material is given to a model:

- by the key `material` of the YAML file of a declared model, as a path relative to the
  YAML file,
- by the class attribute `MATERIAL_FILE` of a model class,
- by the argument `material` of the constructor of a model, as a material name, the
  path to a material JSON file or a `Material`.

## Structure

A material holds material relations, typically one per behaviour law (elasticity,
plasticity, ...), and each material relation holds material properties:

```json
{
  "name": "Steel",
  "description": "A structural steel.",
  "material_relations": [
    {
      "name": "Elastic",
      "metadata": {"author": "J. Doe", "source": "Tensile tests of 2025."},
      "properties": [
        {
          "name": "young_modulus",
          "description": "The Young modulus [MPa].",
          "value": 205000.0,
          "lower_bound": 190000.0,
          "upper_bound": 220000.0,
          "distribution": {"name": "Normal", "mu": 205000.0, "sigma": 5000.0}
        },
        {
          "name": "poisson_ratio",
          "value": 0.3
        }
      ]
    },
    {
      "name": "Plastic",
      "properties": [
        {
          "name": "yield_stress",
          "value": 355.0,
          "lower_bound": 300.0,
          "upper_bound": 400.0,
          "distribution": {"name": "Uniform", "lower": 300.0, "upper": 400.0}
        }
      ]
    }
  ]
}
```

### Material

| Key | Required | Description |
| --- | --- | --- |
| `name` | yes | The name of the material. |
| `description` | no | A description of the material. |
| `material_relations` | no | The material relations, as a list. |
| `grammar_name` | no | The name of the material grammar the material conforms to, so that it is offered as an alternative material for the models declaring this grammar. Left empty, the material is only used by the model naming it. |

### Material relation

| Key | Required | Description |
| --- | --- | --- |
| `name` | yes | The name of the material relation, e.g. `Elastic`. |
| `properties` | no | The material properties, as a list. |
| `metadata` | no | The `author` of the material relation and the `source` of the data it was calibrated on. |
| `tag` | no | A free tag. |

### Material property

| Key | Required | Description |
| --- | --- | --- |
| `name` | yes | The name of the property: the name of the model input it gives the value of. |
| `value` | yes | The value of the property, within its bounds. |
| `description` | no | A description of the property, e.g. with its unit. |
| `lower_bound` | no | The lower bound of the property. By default, `-1e12`. |
| `upper_bound` | no | The upper bound of the property. By default, `1e12`. |
| `distribution` | no | The probability distribution of the property. By default, none: the property is deterministic. |

The `distribution` makes the property stochastic. Its `name` is one of:

- `Normal`, with the mean `mu` and the standard deviation `sigma`,
- `Uniform`, with the bounds `lower` and `upper`, equal to the bounds of the property.

The distribution is truncated to the bounds of the property, so that its samples are
valid values of the property. Truncating a `Uniform` distribution to bounds wider than
its own ones is an error.

## Rules

- **The properties are named after the inputs of the model.** The value of a property
  is the default value of the model input of the same name, and this input is
  classified as a material variable. For a model wrapping a GEMSEO discipline, a
  property which is not an input of the discipline raises a `ValueError` when the model
  is created.
- **The property names shall be unique** over the whole material, whatever their material
  relations.
- **The bounds of a property are within those of the input grammar of the model**,
  when it bounds the input: a looser bound, or a value out of the grammar bounds,
  raises a `ValueError` when the model is created. This way, the samples of the
  uncertain space of the material are valid inputs of the model.

## Usage

The stochastic properties define an uncertain space, e.g. to propagate the material
variability through the model:

```python
from vimseo.material.material import Material

material = Material.from_json("steel.json")
print(material.to_parameter_space())
```

The examples
[Wrap a GEMSEO discipline with a material](../../generated/runnable_examples/02_integrated_models/plot_05_discipline_with_material.md)
and
[Declare a model wrapping a GEMSEO discipline in a YAML file](../../generated/runnable_examples/02_integrated_models/plot_06_declarative_model.md)
use a material.
