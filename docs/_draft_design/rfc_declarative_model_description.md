<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# RFC — Declarative model description in VIMSEO
## Model Card, quantity dictionary, grammar and uncertainties

> **Status of this document**: proposal, to be checked against the actual codebase. Written from the public VIMSEO README (v0.1.6). Items marked ⚠️ require verification in the code before implementation.

---

## 1. Diagnosis

Model input description in VIMSEO is currently spread across heterogeneous mechanisms:

- **GEMSEO grammars** validate input/output structure;
- **uncertainty** can only be expressed through the material (`model.material.to_parameter_space()`);
- **credibility metadata** (assumptions, validity domain, V&V status) has no formal support.

Three limitations follow:

1. **Uncertainty is captive to the material.** A CFD, thermal, or analytical model without a material has nowhere to declare that an input is uncertain.
2. **All uncertainty becomes aleatory.** `to_parameter_space()` produces a distribution; there is no support for epistemic uncertainty (an interval without a law), which is central to ASME V&V 10.
3. **Credibility lives outside the tool.** Assumptions, validity domain, and what has or hasn't been validated live in external documents that drift from the code — yet this is precisely VIMSEO's purpose.

---

## 2. Proposal: three declarative artefacts

| Artefact | Answers | Changes when… |
|---|---|---|
| `model_card.json` | *What does this model do, under which assumptions, how far is it credible?* | the model or its validation status evolves |
| `grammar.json` (+ global `quantities.json`) | *What is a valid input/output value?* | the interface changes |
| `uncertainty.json` | *What do we know about the value of each input?* | knowledge advances (test, measurement, literature) |

Deliberate separation: recalibrating a parameter after a test touches only `uncertainty.json` — neither the grammar nor the model card.

*(Load cases and execution settings are the subject of separate proposals, out of scope here.)*

---

## 3. Model Card (`model_card.json`)

Formalisation of the *Model Identity Card* concept: the model's credibility record, human-readable and machine-exploitable.

```json
{
  "id": "M-PROP-01",
  "version": "1.2.0",
  "name": "Hover rotor power (actuator disk)",
  "authors": ["..."],
  "status": "partially_validated",

  "purpose": "Computes the electrical power required for a given thrust.",
  "intended_use": "Preliminary sizing of VTOL propulsion.",

  "assumptions": [
    { "id": "A1", "text": "Figure of merit constant regardless of disk loading.",
      "verified": false, "impact": "high" },
    { "id": "A2", "text": "No voltage or current limit modelled.",
      "verified": true, "impact": "medium" }
  ],

  "limitations": [
    "Motor heating not modelled (static continuous-current threshold only).",
    "ESC and wiring efficiency not accounted for."
  ],

  "validity_domain": {
    "description": "Verified against manufacturer table, 380-800 g thrust.",
    "bounds": { "T": { "min": 3.7, "max": 7.9, "unit": "N" } }
  },

  "vv_status": {
    "code_verification":    { "done": true,  "evidence": "unit tests, analytical case" },
    "solution_verification":{ "done": false },
    "validation":           { "done": true,  "evidence": "T-Motor MT2216 table, 5 points, <2.5% deviation" },
    "uncertainty_quantification": { "done": false }
  },

  "recommended_actions": [
    "Static bench test of the rear rotor across several operating points to resolve A1."
  ],

  "upstream_models":   ["M-MISSION-01"],
  "downstream_models": ["M-MISSION-02"],

  "references": [{ "type": "datasheet", "id": "T-Motor MT2216", "uri": "..." }]
}
```

**What the tool can do with it** — this is what justifies formalisation over a plain document:

```python
model.card.status                             # -> "partially_validated"
model.card.unverified_assumptions()           # -> [A1]  (with impact)
model.card.is_within_validity_domain(inputs)  # -> False, "T=9.2 N outside [3.7 ; 7.9]"
workflow.credibility_report()                 # aggregates cards across the workflow
```

The last point is the most structurally significant: in a multi-model workflow, **overall credibility is bounded by the weakest link**. Nothing currently allows this to be computed; with model cards it becomes an aggregation.

---

## 4. Quantity dictionary (`quantities.json`) and grammar

### 4.1 Global dictionary, shared across models

```json
{
  "length":          { "dimension": "L",           "unit": "m",  "constraints": { "gt": 0 } },
  "mass":            { "dimension": "M",           "unit": "kg", "constraints": { "gt": 0 } },
  "youngs_modulus":  { "dimension": "M.L^-1.T^-2", "unit": "Pa", "constraints": { "gt": 0 } },
  "figure_of_merit": { "dimension": "1",           "unit": "-",  "constraints": { "gt": 0, "le": 1 },
                       "description": "Rotor hover efficiency" }
}
```

Benefits: unit consistency across coupled models, automatic dimensional checking of couplings, physical constraints declared once (`figure_of_merit <= 1` can no longer be forgotten in an individual model).

### 4.2 Model grammar

```json
{
  "inputs": [
    { "symbol": "T",         "quantity": "thrust",          "role": "physical",  "type": "scalar" },
    { "symbol": "A_disk",    "quantity": "area",            "role": "physical",  "type": "scalar" },
    { "symbol": "FM",        "quantity": "figure_of_merit", "role": "physical",  "type": "scalar" },
    { "symbol": "mesh_size", "quantity": "length",          "role": "numerical", "type": "scalar",
      "affects_results": true }
  ],
  "outputs": [
    { "symbol": "P_elec",    "quantity": "power", "type": "scalar" }
  ]
}
```

A variable **references** a quantity and inherits unit + constraints; it may also declare them locally if no dictionary entry fits (the dictionary is a convenience, not an obligation).

The `role` field distinguishes:

| `role` | Meaning | DOE-sweepable |
|---|---|---|
| `physical` | physical quantity of the model | yes |
| `numerical` | discretisation / solution setting that **conditions the result** | **yes** (this is the basis of discretisation error estimation, an explicit VIMSEO use case) |

⚠️ **To check**: are the GEMSEO grammars used `JSONGrammar` or `PydanticGrammar`? This determines whether `quantities.json` plugs in directly or needs an adaptation layer.

---

## 5. Uncertainties (`uncertainty.json`)

```json
{
  "young_modulus": {
    "nature": "aleatory",
    "domain": { "distribution": "Triangular", "lower": 68e9, "mode": 70e9, "upper": 72e9 },
    "source": "coupon tests, batch A (n=32)",
    "confidence": "high"
  },
  "FM": {
    "nature": "epistemic",
    "domain": { "type": "interval", "min": 0.30, "max": 0.45 },
    "nominal": 0.384,
    "source": "inferred from a single measurement point by subtraction",
    "confidence": "low",
    "reduction_action": "multi-point static bench test"
  },
  "solver_scheme": {
    "nature": "epistemic",
    "domain": { "type": "enum", "values": ["implicit", "explicit"] },
    "nominal": "implicit"
  }
}
```

### 5.1 The central point: `epistemic` != `aleatory`

| | Nature | Representation | Treatment | Reducible |
|---|---|---|---|---|
| **Aleatory** | intrinsic physical variability | probability distribution | propagation by sampling | no |
| **Epistemic** | lack of knowledge | **bare interval, no law** | interval / robustness analysis, or an **explicitly assumed** Bayesian prior | yes, by testing |

Placing a uniform law on epistemic uncertainty is not neutral: it is a Bayesian choice that should be an analysis decision, not a hidden default inside the model declaration.

### 5.2 Proposed API

```python
model.to_parameter_space(nature="aleatory")   # -> GEMSEO ParameterSpace (laws)
model.to_interval_set(nature="epistemic")     # -> bounds, robustness analysis
model.uncertain_inputs(confidence="low")      # -> test prioritisation
model.uncertainty_budget()                    # -> consolidated view for the VVUQ plan
```

`uncertain_inputs(confidence="low")` directly answers "where should the next test be invested?", by crossing low confidence with high influence.

---

## 6. Material as a specialisation

The existing material concept is, structurally, **a set of uncertain variables plus mechanics-specific services**. Making this explicit unlocks its use outside mechanics.

```
UncertainVariableSet                    (core - see section 5)
   |- to_parameter_space()
   |- to_interval_set()
   |- uncertain_inputs()
        ^
        | specialises
   Material                             (vimseo.mechanics - optional extension)
   |- constitutive_law : "linear_elastic_orthotropic" | "hashin_damage" | ...
   |- temperature_dependence
   |- to_solver_card(solver="abaqus")   -> *MATERIAL, *ELASTIC, ...
```

Consequences:

- a **CFD, thermal or analytical** model uses the bare `UncertainVariableSet` layer and never sees `Material`;
- a **mechanics** model uses `Material`, which remains consumable by all generic VVUQ tooling since it *is* an `UncertainVariableSet`;
- solver export is a material service, not a core one — a future `Fluid` (viscosity, equation of state) would follow the same pattern without touching the core.

Implementation: extensions declared via entry points (`vimseo.mechanics`, `vimseo.cfd`); the core depends on none of them.

⚠️ **To check**: exact signature of `Material.to_parameter_space()` and the real scope of the class, to size the base-class extraction.

---

## 7. Backward compatibility

No breaking change required:

- `Material` keeps its public API, it simply inherits from a base class;
- a model without `uncertainty.json` behaves as today (fully deterministic);
- a model without `model_card.json` remains executable, with credibility status `undeclared`;
- `quantities.json` is optional: a variable may declare unit and constraints locally.

All three artefacts are **opt-in**, allowing gradual model-by-model adoption.

---

## 8. Suggested sequencing

| # | Step | Risk | Immediate value |
|---|---|---|---|
| 1 | `quantities.json` + `role` field in the grammar | low (additive) | unit consistency across coupled models |
| 2 | Extract `UncertainVariableSet` from `Material` | low (internal refactor, API unchanged) | uncertainty available outside mechanics |
| 3 | `epistemic` / `aleatory` split + `to_interval_set()` | medium (new analysis concept) | ASME V&V 10 compliance |
| 4 | `model_card.json` + `credibility_report()` | low (metadata) | traceable, aggregatable credibility across a workflow |

Step 2 is the pivot: it changes nothing for current users, but makes steps 3 and 4 possible.

---

## 9. Items to verify in the codebase before implementation

1. Actual content of `IntegratedModelSettings` — does it already contain the seed of a separate settings layer?
2. GEMSEO grammar type in use (`JSONGrammar` vs `PydanticGrammar`).
3. Exact scope and API of `Material`.
4. Any model metadata mechanism not documented in the README.
