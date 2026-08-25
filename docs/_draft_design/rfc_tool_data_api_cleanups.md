<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# RFC — Residual cleanups around the tool data API

> **Status of this document**: proposal, checked against the codebase as of 2026-08-24.
> Companion to the "accept plain dicts and DataFrames in VIMSEO tools" change, which
> introduces `to_dataset()` / `resolve_io_groups()`. The items below were found while
> surveying that surface but were deliberately kept out of its scope.

---

## 1. `execute(inputs=...)` silently resets the tool settings

### Diagnosis

`BaseTool._pre_process_options` ([`base_tool.py:332-371`](../../src/vimseo/tools/base_tool.py))
has three mutually exclusive branches. The middle one:

```python
elif "inputs" in options:
    self._options.update(options["inputs"].model_dump())
    if self._SETTINGS is not None:
        self._options.update(self._SETTINGS().model_dump())
```

`self._SETTINGS()` constructs a **fresh defaults instance** and applies it *after* the
inputs, on top of `self._options`. Anything the user set earlier through
`update_options()` or by mutating `tool.options[...]` is overwritten with the default.

This is reachable today. The documented idiom for pre-setting a tool appears in
[`plot_bending_test_vs_data.py:84-88`](../../docs/runnable_examples/03_verification_vs_data/plot_bending_test_vs_data.py):

```python
verificator.options["metric_names"] = [
    "SquaredErrorMetric", "RelativeErrorMetric", "AbsoluteErrorMetric",
]
```

That example survives only because it then calls `execute(**kwargs)`, which takes the
third branch (`self._opt_grammar(**self._options)`) and preserves `_options`. The same
two lines followed by `execute(inputs=SomeInputs(...))` silently reverts `metric_names`
to `["AbsoluteErrorMetric"]`, and the tool reports the wrong metric with no warning.

The three branches also differ in validation strength, which is itself surprising:

| Call style | Validation at execute time |
|---|---|
| `execute(**kwargs)` | full — merged `Settings(_INPUTS, _SETTINGS)` model is constructed |
| `execute(inputs=I, settings=S)` | `isinstance` checks only |
| `execute(inputs=I)` | `isinstance` check, **plus the settings reset above** |

### Proposal

Apply `self._SETTINGS()` defaults as a *floor*, not a ceiling — only for keys not already
present in `self._options`:

```python
elif "inputs" in options:
    if self._SETTINGS is not None:
        for name, value in self._SETTINGS().model_dump().items():
            self._options.setdefault(name, value)
    self._options.update(options["inputs"].model_dump())
```

`self._options` is already seeded with the full default dump in `__init__`
([`base_tool.py:216-220`](../../src/vimseo/tools/base_tool.py)), so in practice the
`setdefault` loop is a no-op and the branch reduces to "apply the inputs". Keeping it
explicit documents the intent.

### Backward compatibility

Behaviour changes only for callers that pre-set settings *and* use `execute(inputs=...)`
without `settings=` — i.e. only for callers currently getting the wrong answer. No
signature change.

### Verify before implementing

Whether any tool relies on the reset to clear state between two `execute()` calls on the
same instance. `BaseCompositeTool.get_filtered_options` routes the flat option dict to
subtools ([`design_value_tool.py:113-121`](../../src/vimseo/tools/design_value/design_value_tool.py),
[`validation_point.py:228`](../../src/vimseo/tools/validation/validation_point.py)), so
subtool option propagation should be re-checked under repeated execution.

---

## 2. `dataframe_to_dataset` raises `IndexError` on a brace-less column

### Diagnosis

[`datasets.py:313-316`](../../src/vimseo/utilities/datasets.py):

```python
def get_group_name(suffixed_name: str) -> str:
    return (suffixed_name.split(GROUP_SEPARATORS[1])[0]).split(GROUP_SEPARATORS[0])[1]
```

For a plain column `"x"`: `"x".split("}")[0]` → `"x"`, `.split("{")` → `["x"]`, `[1]` →
`IndexError: list index out of range`. A user handed a naked pandas DataFrame gets a bare
`IndexError` with no indication that a `{group}` suffix was expected.

Two further landmines in the same function:

- A variable whose component `0` column is absent is silently dropped from
  `reordered_unique_names` (the `if get_component(name) != "0": continue` filter) while
  still being counted in `unique_names_to_n_components`, producing a mismatched
  `Dataset.from_array` call.
- Component columns must be contiguous and ascending in the DataFrame: the reorder logic
  reorders the *name list*, but `Dataset.from_array` consumes `df.to_numpy()`
  positionally, so out-of-order component columns are silently mis-assigned.

The docstring also documents the wrong convention (`a_name[a_group][a_component]`, while
`GROUP_SEPARATORS = ("{", "}")` makes it `a_name{a_group}[a_component]`). *That one line is
corrected as part of the main change; the rest is left here.*

### Proposal

Raise a typed, actionable error instead of `IndexError`, and validate the two structural
assumptions:

```python
msg = (
    f"Column {name!r} has no group suffix. Expected 'name{{group}}' or "
    f"'name{{group}}[component]'. To pass a plain DataFrame, use to_dataset()."
)
raise ValueError(msg)
```

Plus an explicit check that every variable has a component `0` and that its components are
contiguous and ascending.

### Backward compatibility

Strictly additive: inputs that work today keep working. Inputs that crash today crash with
a better message, or newly raise where they previously produced a silently wrong dataset —
which is the point.

---

## 3. Four incompatible component/group spellings coexist

### Diagnosis

The same conceptual thing — "variable `dplt`, component 3, output group" — is spelled four
different ways across VIMSEO's own I/O surface, and nothing documents the mapping:

| Spelling | Where | Consumer |
|---|---|---|
| `x3_0;x3_1;x3_2` | [`reference_data_vector_different_lengths.csv`](../../docs/runnable_examples/07_validation_case/reference_data_vector_different_lengths.csv) | `ReaderFileDataFrame` → `IODataset.from_txt`, requires an explicit `variable_names_to_n_components` |
| `dplt[0];dplt[1]` | `dataframe_validation_beam_cantilever.csv` | produced by `generate_reference_from_dataset(as_dataset=False)`; no group information at all |
| `dplt{outputs}[0]` | in-memory only | `dataset_to_dataframe(suffix_by_group=True)` ⇄ `dataframe_to_dataset` |
| 3-row `GROUP`/`VARIABLE`/`COMPONENT` header | `dataset_validation_beam_cantilever.csv` | `ReaderFileGemseoDataset` → `IODataset.from_csv`, GEMSEO-native |

The underscore form carries no size information, so `ReaderFileDataFrame` cannot infer it —
GEMSEO ignores the suffix and slices columns positionally. The corresponding inference test
is skipped with a pointer to an upstream issue
([`tests/io/test_io_dataset.py:104`](../../tests/io/test_io_dataset.py),
`test_io_read_dataframe_infer_header`, *"Issue opened in GEMSEO"*).

### Proposal

1. Adopt `name[i]` (bracket, no group) as the single VIMSEO spelling for a component in a
   *mono-index* frame, since it is already what the library **writes**. Keep the 3-row
   header as the canonical *round-trip* format, since it is GEMSEO-native and lossless.
2. Teach `ReaderFileDataFrame` to infer `variable_names_to_n_components` from `name[i]`
   headers, making the setting optional. Deprecate the `name_i` underscore form in VIMSEO's
   own data files (it is ambiguous: `dplt_grid` vs `dplt` component `grid`).
3. Once (2) lands, `to_dataset()` can accept a mono-index DataFrame with `name[i]` columns
   and rebuild vectors without any user-supplied sizes — closing the last gap where a
   DataFrame is strictly less expressive than a dict of 2-D arrays.
4. Track the upstream GEMSEO issue behind the skipped test and unskip it, or implement the
   inference on the VIMSEO side of `ReaderFileDataFrame`.

### Backward compatibility

Steps 1-2 are additive (inference only fires when the setting is absent). Step 3 is new
capability. Only the deprecation of `name_i` in shipped example CSVs is a visible change,
and those files are regenerated by their own examples.

---

## 4. `BayesTool` is the odd one out

### Diagnosis

Every analysis tool takes a `Dataset` except `BayesTool`, whose
[`BayesInputs.data`](../../src/vimseo/tools/bayes/bayes_analysis.py) is a bare
`ndarray = empty(0)`. The seam is visible inside a single example,
[`plot_12_bayesian_calibration.py:78-81`](../../docs/runnable_examples/12_bayesian_calibration/plot_12_bayesian_calibration.py),
where the *same array* is wrapped two different ways within a few lines:

```python
dataset = Dataset.from_array(data_modulus.reshape(-1, 1))
results_normal = statistic_tool.execute(dataset=dataset, tested_distributions=["Normal"])
...
analysis_n.execute(likelihood_dist=Models.NORMAL, prior_dist=prior_normal,
                   data=data_modulus, n_mcmc=N_MCMC)
```

The user must know that `StatisticsTool` wants a `Dataset` and `BayesTool` wants a raw
array, and must reshape by hand for one of them.

### Proposal

Once `to_dataset()` exists, widen `BayesInputs.data` to the same `DatasetInput` annotation
and extract the 1-D sample internally. A 1-D array, a list, a `{"young_modulus": [...]}`
dict and a `Dataset` then all work, and `.reshape(-1, 1)` disappears from user code.

### Backward compatibility

Additive — `ndarray` remains valid input. `BayesTool` currently consumes `data` as a flat
sample vector, so single-variable datasets map onto it unambiguously; a multi-variable
dataset should raise a clear error naming the variable to select.

---

## 5. Missing "passing data to VIMSEO tools" documentation page

### Diagnosis

The `{inputs}`/`{outputs}` convention appears in exactly one runnable example
(`05_solution_verification`) and one docstring. There is no page in `docs/how_to/`
explaining how user data reaches a tool — `run_a_study.md` mentions datasets only in the
context of cache viewing. The nearest thing to an explanation is a comment block inside
[`plot_read_reference_data.py:37-80`](../../docs/runnable_examples/07_validation_case/plot_read_reference_data.py),
which currently states that *"the raw experimental data is not directly compatible with
VIMSEO tools"* — a statement the main change makes false.

Users consequently import `GROUP_SEPARATORS`, `SEP` and `dataframe_to_dataset` from
`vimseo.utilities.datasets`, none of which is re-exported by `vimseo.api`.

### Proposal

Add `docs/how_to/passing_data_to_tools.md` covering, in order of decreasing frequency:

1. dict of arrays (the default; vectors as 2-D arrays; ragged sequences NaN-padded);
2. mono-index DataFrame (CSV-loaded data);
3. nested `{"inputs": ..., "outputs": ...}` dict, for when no model is available to resolve
   roles;
4. how roles are resolved when they are *not* given explicitly (tool settings, then the
   model grammars);
5. `Dataset` / `IODataset` as the advanced, lossless round-trip format, cross-linking
   `dataset_to_dataframe` ⇄ `dataframe_to_dataset` and the 3-row CSV header.

Written after the main change lands, so the page documents the final API rather than the
transition.

---

## 6. Readability nit — shadowed `batch` in the stochastic validation case example

### Diagnosis

[`plot_stochastic_validation_case_straightbeammodel.py:128-157`](../../docs/runnable_examples/07_validation_case/plot_stochastic_validation_case_straightbeammodel.py)
zips `[1, 2, 3]` against a list comprehension that rebinds the *same name*:

```python
for batch, reference_data in zip(
    [1, 2, 3],
    [ReaderFileDataFrame().execute(... f"..._{batch}.csv" ...).dataset
     for batch in [1, 2, 3]],
    strict=False,
):
```

This is **correct** — comprehensions have their own scope in Python 3, and the two
sequences are paired in order — but a reader must reason about comprehension scoping to
convince themselves of it, and the duplicated `[1, 2, 3]` literal is a live correctness
dependency between the two arguments.

### Proposal

Bind the batches once and build the reference data inside the loop:

```python
batches = [1, 2, 3]
for batch in batches:
    reference_data = ReaderFileDataFrame().execute(...).dataset
```

The `strict=False` on the `zip` also becomes unnecessary. Note this example is rewritten
anyway by the main change (the 19-line reader settings block collapses), so this is best
folded into that edit rather than done separately.

---

## Priority

| # | Item | Severity | Effort |
|---|---|---|---|
| 1 | `execute(inputs=...)` resets settings | **wrong results, silent** | S |
| 2 | `dataframe_to_dataset` `IndexError` + silent mis-assignment | poor DX, one silent-corruption path | S |
| 4 | `BayesTool.data` inconsistency | inconsistency only | S |
| 5 | Documentation page | discoverability | M |
| 3 | Unify component spellings | design debt, unblocks DataFrame vectors | M–L |
| 6 | `batch` shadowing | readability | XS |

Items 1 and 2 are independent of the main change and can land first. Items 4 and 5 depend
on it. Item 3 is the only one with an upstream (GEMSEO) dependency.
