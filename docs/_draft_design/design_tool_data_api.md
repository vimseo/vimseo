<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Accept plain dicts and DataFrames in VIMSEO tools

> **Status of this document**: implementation plan, checked against the codebase as of
> 2026-08-24 and implemented on the `feat/tool-data-api` branch. Kept as the design record
> for the `to_dataset()` / `resolve_io_groups()` change.

## Context

To feed a VIMSEO tool today, a user must learn two concepts that have nothing to do with
VV&UQ: the GEMSEO `Dataset` (a 3-level MultiIndex DataFrame) and VIMSEO's private
`name{group}[component]` column convention. The anchor case is
[plot_tan_open_hole_convergence.py:142-166](../../docs/runnable_examples/05_solution_verification/plot_tan_open_hole_convergence.py#L142-L166):
values are collected in lists, assembled into a DataFrame, renamed with `{inputs}`/`{outputs}`
braces, then converted with `dataframe_to_dataset`.

Exploration showed the problem is both worse and easier to fix than it looks:

- **That particular conversion is already dead weight.** `SolutionVerificationSettings.simulated_data`
  is typed `Dataset | DataFrame | None` and the tool only ever calls
  `get_view(variable_names=...)`, never `group_names=` — see
  [solution_verification.py:334-345](../../src/vimseo/tools/verification/solution_verification.py#L334-L345).
  Groups are ceremony, not information, for this tool.
- **The worst case is 4 hops and ~20 lines**, in
  [plot_stochastic_validation_straightbeam.py:150-169](../../docs/runnable_examples/06_validation_point/plot_stochastic_validation_straightbeam.py#L150-L169),
  where the user string-formats the internal constant `GROUP_SEPARATORS` to build column names.
- **No `dict → Dataset` entry point exists.** That idiom is open-coded three times inside the
  library with three different size-inference strategies
  ([validation_case.py:181-190](../../src/vimseo/tools/validation_case/validation_case.py#L181-L190),
  `job_bundle.py:568`, `generate_validation_reference.py:114`).
- **Vectors are supported but undiscoverable.** `dataframe_to_dataset` does handle multi-component
  variables via a `name{group}[i]` suffix — its docstring says `name[group][component]`, which is
  wrong. Meanwhile the CSV readers use `name_0`/`name_1`. Three incompatible component spellings
  coexist in the docs' own data files.
- **6 of 32 examples carry dataset-assembly boilerplate**; the other 26 need none, so the fix is
  targeted, not systemic.

Outcome: a user passes the data they already have — a dict of arrays, or a plain DataFrame — and
never meets `Dataset`, `dataframe_to_dataset`, or `GROUP_SEPARATORS`. Vectors work naturally
because a dict value can be a 2-D array.

## Design: two layers

Group semantics are load-bearing in some tools and pure ceremony in others, so coercion splits in
two. This matters because [workflow_step.py:247-260](../../src/vimseo/workflow/workflow_step.py#L247-L260)
constructs `_INPUTS(**inputs)` directly and **bypasses** `BaseTool._pre_process_options` — so
type coercion must live on the Pydantic annotation, not in the tool plumbing.

### Layer 1 — `to_dataset()`: type coercion, no context needed

New public function in [src/vimseo/utilities/datasets.py](../../src/vimseo/utilities/datasets.py), re-exported
from [src/vimseo/api.py](../../src/vimseo/api.py) so users never import from `utilities`:

```python
def to_dataset(
    data: Dataset | DataFrame | Mapping[str, Any],
    input_names: Iterable[str] = (),
    output_names: Iterable[str] = (),
) -> IODataset
```

Dispatch:

| Input | Handling |
|---|---|
| `Dataset` / `IODataset` | returned unchanged (re-wrapped as `IODataset` if needed) |
| `Mapping` whose values are all `Mapping` | top-level keys are group names — the **nested form** `{"inputs": {...}, "outputs": {...}}` |
| `Mapping` of array-likes | **flat form**; split by `input_names`/`output_names` when given, else all in `Dataset.DEFAULT_GROUP` |
| `DataFrame`, MultiIndex columns | `Dataset.from_dataframe` |
| `DataFrame`, any column containing `{` | `dataframe_to_dataset` (legacy path, preserved) |
| `DataFrame`, plain mono-index columns | `df.to_dict(orient="list")` then the flat form |

Component handling — the reason dicts beat DataFrames:

- `ndim == 1` → reshape `(n, 1)`, one component.
- `ndim == 2` → `(n_entries, n_components)`, vector variable.
- ragged sequence of 1-D arrays → NaN-pad to max length, matching the existing convention
  (`decode_stringified_vectors` pads at
  [encoded_to_numerical_vectors.py:66-80](../../src/vimseo/utilities/encoded_to_numerical_vectors.py#L66-L80);
  `DeterministicValidationCase` strips at `validation_case.py:152-156`).
- scalars broadcast to `n_entries`.
- inconsistent `n_entries` across variables → `ValueError` naming the offending variable.

Build with one `IODataset.from_array(...)` carrying `variable_names_to_n_components` and
`variable_names_to_group_names` — the idiom already at
[validation_case.py:181-190](../../src/vimseo/tools/validation_case/validation_case.py#L181-L190).
Always return `IODataset`: it is a purely additive subclass of `Dataset`, so it satisfies both
`Dataset`-annotated and `IODataset`-annotated fields (a field typed `IODataset` currently *rejects*
a plain `Dataset` — a latent trap this removes).

### Layer 2 — `resolve_io_groups()`: group assignment, needs the model

```python
def resolve_io_groups(
    dataset: Dataset,
    model: IntegratedModel | None = None,
    input_names: Iterable[str] = (),
    output_names: Iterable[str] = (),
) -> IODataset
```

- If `INPUT_GROUP` or `OUTPUT_GROUP` is already present → return unchanged (full back-compat).
- If only `DEFAULT_GROUP` → inputs from explicit `input_names`, else `model.input_grammar.names`
  intersected with the dataset variables; outputs from explicit `output_names`, else
  `model.get_output_data_names(remove_metadata=True)` intersected likewise. Move those variables
  into the two groups; **leave unmatched variables in `DEFAULT_GROUP`** so carrier columns
  (`batch`, `nominal_length`, …) survive.
- Raise a clear, actionable error when neither a model nor explicit names can resolve the roles.

This generalises the one-off already at
[verification_vs_model.py:93-94](../../src/vimseo/tools/verification/verification_vs_model.py#L93-L94),
which becomes a call to the helper.

### Pydantic wiring

Define alongside `to_dataset`:

```python
DatasetInput = Annotated[IODataset, BeforeValidator(to_dataset)]
```

`BaseInputs` already sets `arbitrary_types_allowed=True`, so the `IODataset` isinstance check stays;
the `BeforeValidator` runs ahead of it. Because coercion lives on the annotation, the Streamlit
workflow path gets it for free.

## Work items

### 1. Converter + resolver (foundation)

- `to_dataset`, `resolve_io_groups`, `DatasetInput` in
  [src/vimseo/utilities/datasets.py](../../src/vimseo/utilities/datasets.py).
- Export `to_dataset` from [src/vimseo/api.py](../../src/vimseo/api.py).
- Fix the stale `dataframe_to_dataset` docstring (it documents `name[group][component]`; the code
  reads `name{group}[component]`) and mark it as the advanced round-trip counterpart of
  `dataset_to_dataframe`. Keep it public and working — 4 internal call sites depend on it
  (`db_viewer_model.py:58`, `validation_case_result.py:128`, `validation_point.py:450`,
  `error_scatter_matrix_plot.py:49`).

### 2. Widen the dataset-typed fields

Replace `Dataset | None` / `IODataset | None` with `DatasetInput | None` in each `_INPUTS`
(and the two `_SETTINGS` that hold datasets). Same one-line pattern everywhere:

| Tool | Field | File |
|---|---|---|
| `CustomDOETool` | `input_dataset` | [custom_doe.py:66](../../src/vimseo/tools/doe/custom_doe.py#L66) |
| `CodeVerificationAgainstData` | `reference_data` | [verification_vs_data.py:42](../../src/vimseo/tools/verification/verification_vs_data.py#L42) |
| `CodeVerificationAgainstModel` | `input_dataset` | `verification_vs_model.py` |
| `DeterministicValidationCase` | `reference_data` | [validation_case.py:69](../../src/vimseo/tools/validation_case/validation_case.py#L69) |
| `StochasticValidationPoint` | `measured_data` | [validation_point.py:71](../../src/vimseo/tools/validation/validation_point.py#L71) |
| `SurrogateTool` | `dataset` | `surrogate/surrogate.py` |
| `StatisticsTool` | `dataset` | `statistics/statistics_tool.py` |
| `CalibrationStep` | `reference_data: dict[str, DatasetInput]` | `calibration/calibration_step.py` |
| `DiscretizationSolutionVerification` | `simulated_data` (in `_SETTINGS`) | [solution_verification.py:204](../../src/vimseo/tools/verification/solution_verification.py#L204) |
| `SolutionVerificationCase` | `results`, `dummy` (in `_SETTINGS`) | `solution_verification_case.py` |

### 3. Wire `resolve_io_groups` into the group-dependent tools

Insert one call immediately after the option is read, in the six tools where groups are actually
load-bearing:

- [custom_doe.py:108](../../src/vimseo/tools/doe/custom_doe.py#L108) — also needs
  `variable_names_to_n_components`, which `to_dataset` now populates correctly for vectors.
- [verification_vs_data.py:76](../../src/vimseo/tools/verification/verification_vs_data.py#L76)
- [validation_case.py:121](../../src/vimseo/tools/validation_case/validation_case.py#L121)
- [validation_point.py:190](../../src/vimseo/tools/validation/validation_point.py#L190) — **also add an
  `input_names` field to `StochasticValidationPointSettings`.** It has `output_names` but no
  `input_names`, so `_measured_input_names` at line 194 currently has the dataset as its only
  possible source.
- `surrogate/surrogate.py` — GEMSEO's `create_surrogate` requires proper I/O groups.
- `calibration/calibration_step.py` — per load case, model taken from the `name_to_models` setting.

And replace the ad-hoc rename at
[verification_vs_model.py:93-94](../../src/vimseo/tools/verification/verification_vs_model.py#L93-L94)
with the helper.

### 4. Rewrite the examples that teach the ceremony

- **05 solution verification** — delete the import, the rename dict and the apologetic comment;
  pass `simulated_data=convergence_table` directly (keep the DataFrame for its `print`).
  Removes 11 lines and one whole concept. *This one already works today.*
- **06 validation point** — pass the filtered `df` with `input_names=measured_inputs`,
  `output_names=measured_outputs`. Drops the `GROUP_SEPARATORS` and `dataframe_to_dataset`
  imports and the 6-line rename loop.
- **03 verification vs data** — replace `IODataset().from_array(...)` with a plain dict.
  Also fix the truncated comment at lines 60-61 (it promises a CSV snippet that is missing).
- **07 validation case on vectors** — show the dict-of-2-D-arrays form for the ragged vector case
  next to the existing `ReaderFileDataFrame` path (that example is *about* the CSV reader, so the
  reader stays).
- **07 read reference data** — update the paragraph at lines 37-80 that currently states raw
  experimental data "is not directly compatible with VIMSEO tools"; it now is.

### 5. Tests

- New `tests/utilities/test_to_dataset.py`: flat dict of scalars; flat dict with a 2-D array;
  ragged sequences NaN-padded; nested group dict; mono-index DataFrame; `{group}` DataFrame
  back-compat; `Dataset` passthrough; `ValueError` on inconsistent `n_entries`.
- New tests for `resolve_io_groups`: already-grouped passthrough, resolution from model grammars,
  resolution from explicit names, unmatched variables left in `DEFAULT_GROUP`, unresolvable error.
- Add a dict-input parametrization to each affected tool test. Existing fixtures to extend:
  `tests/tools/test_doe.py:52`, `tests/tools/verification/test_verification_vs_data.py:35`,
  `tests/tools/test_validation_case.py:43`, `tests/tools/test_validation_point.py:51`,
  `tests/tools/verification/test_solution_verification.py:199`.

## Risks

- **Streamlit dashboard introspection.**
  [dashboard_workflow_model.py:107-124](../../src/vimseo/dashboards/workflow/dashboard_workflow_model.py#L107-L124)
  does `get_type_hints(tool._INPUTS)[attr_name]` to pick a widget. It will now receive
  `Annotated[IODataset, BeforeValidator(...)]`. Unwrap with `typing.get_origin`/`get_args` there,
  and verify the workflow dashboard still renders.
- **`extra="forbid"`** on both bases means the new `input_names` setting on
  `StochasticValidationPointSettings` is a deliberate API addition — intended, and it keeps typos
  failing loudly.
- `to_dataset` returning `IODataset` where `Dataset` was returned before is safe (additive
  subclass), but grep for `type(...) is Dataset` before assuming so.

## Explicitly out of scope

Five issues found during exploration are deliberately excluded per the chosen scope. They are
written up as **Appendix A**, to be committed as
`docs/_draft_design/rfc_tool_data_api_cleanups.md` (matching the existing
`docs/_draft_design/rfc_run_component_flag.md` convention) as the first task of implementation.

## Verification

1. `pytest tests/utilities/test_to_dataset.py -v` — converter unit tests.
2. `pytest tests/tools -m "not slow and not very_slow"` — no regression in the tool suite.
3. Run the four rewritten examples end to end and confirm the printed metrics match the values
   from the current versions:
   `python docs/runnable_examples/05_solution_verification/plot_tan_open_hole_convergence.py`
   (and 03, 06, 07-vectors). The `q_converged` / error-metric numbers must be identical — the
   change is plumbing only.
4. `ruff check src/ && ruff format --check src/`.
5. `dashboard_workflow` — open the Streamlit app, add a tool with a dataset input, confirm the
   widget still renders after the annotation change.
6. Spot-check back-compat: an existing script passing a fully grouped `IODataset` must behave
   exactly as before (covered by the untouched tool tests).

---

# Appendix A — RFC for the out-of-scope items

The plan carried a full RFC draft here. It has since been committed as
[rfc_tool_data_api_cleanups.md](rfc_tool_data_api_cleanups.md) and is not duplicated:

1. `execute(inputs=...)` silently resets the tool settings
2. `dataframe_to_dataset` raises `IndexError` on a brace-less column
3. Four incompatible component/group spellings coexist
4. `BayesTool` is the odd one out
5. Missing "passing data to VIMSEO tools" documentation page
6. Readability nit — shadowed `batch` in the stochastic validation case example

---

# Appendix B — Example rewrites, before / after

Four examples change. Every "after" produces byte-identical numerical results — the edits are
plumbing only.

## B.1 — `05_solution_verification/plot_tan_open_hole_convergence.py`

The anchor case. **Works today without any library change**: `simulated_data` is already typed
`Dataset | DataFrame | None`.

**Before** — 1 import + 16 lines, and the tool call:

```python
from vimseo.utilities.datasets import dataframe_to_dataset
...
convergence_table = DataFrame({
    "dx": dx_values,
    "sigma_xx_probe": probe_stresses,
    "sigma_xx_peak": peak_stresses,
    "sigma_xx_r": sigma_xx_r_values,
    "sigma_xx_d0": sigma_xx_d0_values,
})
print(convergence_table)

# The tool consumes an ``IODataset``. We assemble it from the convergence table
# with the ``dataframe_to_dataset`` helper, using the ``name{group}`` naming
# convention to place ``dx`` in the input group and the four stresses in the
# output group:
dataset = dataframe_to_dataset(
    convergence_table.rename(
        columns={
            "dx": "dx{inputs}",
            "sigma_xx_probe": "sigma_xx_probe{outputs}",
            "sigma_xx_peak": "sigma_xx_peak{outputs}",
            "sigma_xx_r": "sigma_xx_r{outputs}",
            "sigma_xx_d0": "sigma_xx_d0{outputs}",
        }
    )
)
...
verificator.execute(
    simulated_data=dataset,
    element_size_variable_name="dx",
    abscissa_name="dx",
    output_name="sigma_xx_probe",
)
```

**After** — the whole conversion block and its import are deleted; the table goes in as-is:

```python
convergence_table = DataFrame({
    "dx": dx_values,
    "sigma_xx_probe": probe_stresses,
    "sigma_xx_peak": peak_stresses,
    "sigma_xx_r": sigma_xx_r_values,
    "sigma_xx_d0": sigma_xx_d0_values,
})
print(convergence_table)
...
verificator.execute(
    simulated_data=convergence_table,
    element_size_variable_name="dx",
    abscissa_name="dx",
    output_name="sigma_xx_probe",
)
```

The `DataFrame` now exists purely for its `print`. If that display is not wanted, the dict the
loop already builds goes straight in and the `pandas` import disappears too:

```python
verificator.execute(
    simulated_data={
        "dx": dx_values,
        "sigma_xx_probe": probe_stresses,
        "sigma_xx_peak": peak_stresses,
        "sigma_xx_r": sigma_xx_r_values,
        "sigma_xx_d0": sigma_xx_d0_values,
    },
    element_size_variable_name="dx",
    abscissa_name="dx",
    output_name="sigma_xx_probe",
)
```

**Delta:** −17 lines, −1 import, −2 concepts (`Dataset`, `{group}` convention).

## B.2 — `06_validation_point/plot_stochastic_validation_straightbeam.py`

The heaviest path in the repo: CSV → DataFrame → renamed DataFrame → Dataset, with the internal
constant `GROUP_SEPARATORS` string-formatted in user code.

**Before** — 3 imports + 20 lines:

```python
from vimseo.utilities.datasets import GROUP_SEPARATORS
from vimseo.utilities.datasets import SEP
from vimseo.utilities.datasets import dataframe_to_dataset
...
measured_inputs = ["width", "height", "imposed_dplt"]
measured_outputs = ["reaction_forces"]
...
df = read_csv(csv_path, delimiter=SEP)
df = df[df["batch"] == batch]

# Then the reference data are filtered to retain only the measured quantities,
# and converted to a GEMSEO Dataset:
df = df[measured_inputs + measured_outputs]
variable_names_to_group_names = dict.fromkeys(measured_inputs, IODataset.INPUT_GROUP)
variable_names_to_group_names.update(
    dict.fromkeys(measured_outputs, IODataset.OUTPUT_GROUP)
)
for name, group_name in variable_names_to_group_names.items():
    df.rename(
        columns={name: f"{name}{GROUP_SEPARATORS[0]}{group_name}{GROUP_SEPARATORS[1]}"},
        inplace=True,
    )
measured_data = dataframe_to_dataset(df)
print("The measured data as a GEMSEO Dataset: ", measured_data)
```

**After** — the roles are stated once, where they are already declared:

```python
from vimseo.utilities.datasets import SEP
...
measured_inputs = ["width", "height", "imposed_dplt"]
measured_outputs = ["reaction_forces"]
...
df = read_csv(csv_path, delimiter=SEP)
measured_data = df[df["batch"] == batch]
...
validation_point_tool.execute(
    inputs=StochasticValidationPointInputs(
        model=model,
        measured_data=measured_data,
        uncertain_input_space=material.to_parameter_space(),
    ),
    settings=StochasticValidationPointSettings(
        input_names=measured_inputs,       # new setting (work item 3)
        output_names=measured_outputs,
        metric_names=[...],
        nominal_data=nominal_values,
        n_samples=4,
    ),
)
```

Note the column filter `df[measured_inputs + measured_outputs]` is no longer needed either:
`resolve_io_groups` leaves unmatched columns (`batch`, `nominal_length`) in `DEFAULT_GROUP`
rather than choking on them.

**Delta:** −13 lines, −2 imports, −1 leaked internal constant.

## B.3 — `03_verification_vs_data/plot_bending_test_vs_data.py`

Roles here are fully derivable from the model — `height`/`width` are model inputs,
`maximum_dplt`/`reaction_forces` are model outputs — so nothing needs to be declared at all.

**Before** — 1 import + 13 lines, with the data transposed into a row-major literal:

```python
from gemseo.datasets.io_dataset import IODataset
...
# We also need a reference dataset.
# Here we do it programmatically, but we can also create it from a csv file:
# ``
reference_data = IODataset().from_array(
    data=[[10.0, 10.0, -4.0, -12.0], [15.0, 10.0, -6.0, -40.0]],
    variable_names=["height", "width", "maximum_dplt", "reaction_forces"],
    variable_names_to_group_names={
        "height": "inputs",
        "width": "inputs",
        "maximum_dplt": "outputs",
        "reaction_forces": "outputs",
    },
)
```

(The comment is also truncated — it promises a CSV alternative, then stops at a dangling
backtick.)

**After** — column-major, so each variable's values sit next to its name:

```python
# The reference data. A dict of arrays is enough: the tool reads the model's
# grammars to tell inputs from outputs.
reference_data = {
    "height": [10.0, 15.0],
    "width": [10.0, 10.0],
    "maximum_dplt": [-4.0, -6.0],
    "reaction_forces": [-12.0, -40.0],
}
```

**Delta:** −7 lines, −1 import, and the truncated comment is replaced rather than patched.

## B.4 — `07_validation_case/plot_deterministic_validation_case_on_vectors.py`

This example is *about* the CSV reader, so the reader stays. What changes is that the dict form
is shown alongside it as the programmatic equivalent — and it is the clearest demonstration that
dicts handle vectors natively, including ragged ones.

The backing CSV is three lines:

```text
x3_0;x3_1;x3_2;x1;x2;y4
1;2;;1;6.0;3.3
3;4;5;2;7.0;14.4
```

**Before** — 19 lines, and the user must count the components of `x3` by hand:

```python
reference_data = (
    ReaderFileDataFrame()
    .execute(
        settings=ReaderFileDataFrameSettings(
            file_name="reference_data_vector_different_lengths.csv",
            variable_names=["x3", "x1", "x2", "y4"],
            variable_names_to_group_names={
                "x1": IODataset.INPUT_GROUP,
                "x2": IODataset.INPUT_GROUP,
                "x3": IODataset.INPUT_GROUP,
                "y4": IODataset.OUTPUT_GROUP,
            },
            variable_names_to_n_components={
                "x3": 3,
            },
        ),
    )
    .dataset
)
```

**After** — added as a second, equivalent construction; sizes and the NaN padding are inferred
from the data itself:

```python
# The same reference data, built programmatically. ``x3`` is a vector of
# varying length: shorter samples are NaN-padded to the longest one, exactly
# as the blank cells in the csv file are.
reference_data = {
    "x1": [1, 2],
    "x2": [6.0, 7.0],
    "x3": [array([1.0, 2.0]), array([3.0, 4.0, 5.0])],
    "y4": [3.3, 14.4],
}
```

**Delta:** −15 lines for the equivalent construction, and `variable_names_to_n_components`
disappears — the one piece of bookkeeping a user cannot get wrong by hand if they never write it.

## B.5 — Summary

| Example | Lines removed | Imports removed | Concepts a user no longer meets |
|---|---|---|---|
| 05 solution verification | 17 | 1 | `Dataset`, `{group}` convention |
| 06 validation point | 13 | 2 | `Dataset`, `{group}`, `GROUP_SEPARATORS` |
| 03 verification vs data | 7 | 1 | `IODataset`, `variable_names_to_group_names` |
| 07 validation case on vectors | 15 | — | `variable_names_to_n_components` |

Unchanged and still recommended as the zero-boilerplate reference paths already in the repo:
`bending_test_analytical_reference_dataset(shift=10.0)["Cantilever"]` (example 07 straightbeam)
and `generate_reference_from_parameter_space(model, space, n_samples=6, as_dataset=True)`
(example 08).
