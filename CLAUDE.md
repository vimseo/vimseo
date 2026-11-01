<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Python environment:** run the tests, the examples and any script with the tox
environment `.tox/py312/` (`.tox/py312/bin/python` on Linux,
`.tox/py312/Scripts/python.exe` on Windows), which holds every extra and the dev
dependencies with VIMSEO installed in editable mode. Do not use `.venv/`: it is not
kept in sync with `pyproject.toml` (e.g. it lacks `kaleido` and `pyvista`, so tests
needing them are silently skipped).

```bash
.tox/py312/bin/python -m pytest tests/analysis_nodes/test_doe.py          # Linux
.tox/py312/Scripts/python.exe -m pytest tests/analysis_nodes/test_doe.py  # Windows
```

**Install (editable, with every extra and the dev dependencies):**
```bash
uv pip install -e ".[all]" --group dev
# or via tox:
tox -e py312 -- --co  # list tests without running
```

`[all]` and `dev` come from two different mechanisms: `all` is an *extra*
(`[project.optional-dependencies]`, selected with brackets), whereas `dev` is a
*dependency group* (`[dependency-groups]`, selected with `--group`). Writing `".[dev]"`
silently installs nothing extra.

Install the mandatory dependencies only -- the profile an HPC user gets -- with
`uv pip install -e .`. See the Optional dependencies section below.

**Run tests (fast tests only, default):**
```bash
pytest
# or via tox (full profile -- every extra):
tox -e py312
# mandatory dependencies only (the HPC user profile):
tox -e core-py312
```

**Run a single test file:**
```bash
pytest tests/analysis_nodes/test_doe.py
```

**Run tests by marker:**
```bash
pytest -m fast
pytest -m "not slow and not very_slow"
```

**Lint and format (ruff):**
```bash
ruff check src/
ruff format src/
# or via tox (runs pre-commit with all checks):
tox -e check
```

**Build docs (serves locally):**
```bash
tox -e doc
```

**Build distribution:**
```bash
tox -e dist
```

## Architecture

VIMSEO is a VV&UQ (Verification, Validation & Uncertainty Quantification) framework. It wraps simulation models and provides analysis nodes to assess simulation credibility. The library is built on top of [GEMSEO](https://gemseo.readthedocs.io/), a Python MDO library — VIMSEO models are GEMSEO `Discipline` subclasses.

### Model layer (`src/vimseo/core/`)

`IntegratedModel` ([base_integrated_model.py](src/vimseo/core/base_integrated_model.py)) is the central abstraction. It is a GEMSEO `Discipline` that wraps one or more `BaseComponent` objects representing model execution stages. Two concrete model base classes exist:

- **`PreRunPostModel`** ([pre_run_post_model.py](src/vimseo/core/pre_run_post_model.py)): Chains a pre-processor, run-processor, and post-processor. Component class names follow the convention `{Family}_{LoadCase}` (e.g., `PreStraightBeam_Cantilever`). This is why the ruff `N801` rule (CapWords) is disabled.
- **`BaseDisciplineModel`** ([base_discipline_model.py](src/vimseo/core/base_discipline_model.py)): Wraps a single GEMSEO `Discipline` directly.

A `LoadCase` encapsulates the boundary conditions and parameters for a model run. Models are discovered via `ModelFactory` (GEMSEO plugin mechanism, registered via the `gemseo_plugins` entry point in `pyproject.toml`).

### Analysis nodes layer (`src/vimseo/analysis_nodes/`)

All analysis nodes inherit from `BaseAnalysisNode` ([base_analysis_node.py](src/vimseo/analysis_nodes/base_analysis_node.py)). The analysis node pattern:

- Class attributes `_INPUTS` (a `BaseInputs` subclass) and `_SETTINGS` (a `BaseSettings` subclass) define Pydantic models for validation.
- `execute(inputs=..., settings=...)` accepts instances of those Pydantic models, or falls back to keyword arguments.
- Results are stored in `analysis_node.result` (a `BaseResult` subclass) and persisted via `analysis_node.save_results()` to HDF5.
- A result is visualized without its analysis node, e.g. once loaded from an archive:
  `result.plot(**settings)` returns its figures (Plotly or matplotlib) and
  `result.to_dataframes()` its numerical values as DataFrames. A result class declares
  its figures in `_create_figures()` and its settings in `_PLOT_SETTINGS`, whose
  fields are flat and default to "everything"; `get_plot_choices()` gives the names
  accepted by the settings selecting names.
- `vimseo.api.load_analysis_node_results(refs)` / `load_model_results(refs)` load one or many
  results from their references (identifier, `analysis-node-run:` / `run:`, path, `runs:/`,
  [analysis_node_archive/uri.py](src/vimseo/storage_management/analysis_node_archive/uri.py)) and always
  return a collection (`AnalysisNodeResults` / `ModelResults`, [results/collection.py](src/vimseo/results/collection.py));
  `open_model_results(**archive)` / `open_analysis_node_results` open a whole archive, explored with
  `filter(query=...)`, `ignoring`, `varying_inputs`, `families(along=...)`, `duplicates`.

**Calling analysis nodes:** prefer `analysis_node.execute(inputs=MyAnalysisNodeInputs(...), settings=MyAnalysisNodeSettings(...))`
(the analysis node's `_INPUTS` / `_SETTINGS` classes) over keyword arguments, in examples, tests and
new code. The models validate eagerly and keep inputs and settings distinct; keyword
arguments remain supported for backward compatibility.

Available analysis node categories: DOE, sensitivity analysis, calibration, verification (solution + vs-data + vs-model), validation (point + case), surrogate modelling, statistics, Bayesian analysis, design value.

### Storage (`src/vimseo/storage_management/`)

`IntegratedModelSettings.archive_manager` selects the storage backend, resolved by
`get_archive_class()` in [storage_management/__init__.py](src/vimseo/storage_management/__init__.py):
- `"DirectoryArchive"` — stores results in a local directory structure. **This is the default**
  ([configuration_settings.py:71](src/vimseo/config/configuration_settings.py)).
- `"MlflowArchive"` — stores model runs in an MLflow tracking server. Requires the `mlflow`
  extra, and is imported lazily so that the model layer does not depend on mlflow.

The runs are grouped by **study** (`study_name`, default `default_study`, `VIMSEO_STUDY_NAME`):
a simulation is in `{root}/{study}/{model}/{load_case}/{run_id}/results.json`, written with
`status=RUNNING` when it starts; in MLflow a study is one experiment and the runs are told apart
by the tag `vimseo.kind`. The identifiers are time ordered (`{UTC date}_{uuid prefix}`).

The **analysis node results** are archived separately, by `open_analysis_node_archive()` in
[analysis_node_archive/__init__.py](src/vimseo/storage_management/analysis_node_archive/__init__.py), selected
by the `archive_manager` setting of an analysis node, else `config.analysis_node_archive_manager`, else
`config.run_archive_manager` (`"none"` disables it; the tests disable it in `conftest.py`):
- `DirectoryAnalysisNodeArchive` — `{root}/{study}/analysis_nodes/{analysis_node_name}/{analysis_node_run_id}/` holds the result HDF5
  and a JSON summary.
- `MlflowAnalysisNodeArchive` — one MLflow run per analysis node run in the experiment of the study, the run of a
  sub-analysis node nested in the run of its parent. The result HDF5 and the summary are artifacts,
  the searchable fields are `vimseo.*` tags and the settings are params.

An analysis node run is identified by its `analysis_node_run_id` (`result.metadata.analysis_node_run_id`); its simulations
carry it too. `search_model_results(**archive, query=...)` / `search_analysis_node_runs` list the runs
without loading them (the query uses the `pandas.DataFrame.query` syntax, with `or`).

Scratch storage is a separate mechanism: `DirectoryScratch`
([scratch_storage.py](src/vimseo/storage_management/scratch_storage.py)) is always used and
is not selectable through `archive_manager`.

### Optional dependencies

The mandatory dependencies are limited to what is needed to build a model, execute it and
serialize its results, so that VIMSEO installs on a machine with no graphical stack. The
rest is shipped by extras: `dashboard` (streamlit), `mlflow`, `mesh` (pyvista/vtk) and
`jax`. Import anything they provide through `import_optional()` in
[utilities/optional_dependencies.py](src/vimseo/utilities/optional_dependencies.py), never
at module top level.

**Exception:** `TanOpenHole` is a core model (`meshio` is mandatory, so it stays
discoverable and instantiable) but its `PostFieldExtraction` step reads the flux field
back with pyvista, so *executing* it -- not just creating it -- needs the `mesh` extra.
[problems/tan_oh/tan_oht.py](src/vimseo/problems/tan_oh/tan_oht.py) is the only model with
this split; before adding a similar one, prefer keeping execution extra-free.

This matters because GEMSEO's `BaseFactory` swallows import failures during class
discovery: a top-level import of an optional dependency does not raise, it just makes the
class silently disappear from the factory. [tests/test_optional_dependencies.py](tests/test_optional_dependencies.py)
is the guard rail. `tox -e py312` runs the full profile (every extra); `tox -e core-py312`
runs the core profile (mandatory dependencies only).

### Workflow engine (`src/vimseo/workflow/`)

`Workflow` ([workflow.py](src/vimseo/workflow/workflow.py)) chains analysis nodes using GEMSEO's `MDAChain`. Workflows can be serialised to/from JSON and executed via the `workflow_executor` CLI entry point. The `dashboard_workflow` Streamlit app lets users build workflows interactively.

### Settings / configuration

All settings classes inherit from `BaseSettings` (Pydantic `BaseModel` with `extra="forbid"`) in [analysis_nodes/base_settings.py](src/vimseo/analysis_nodes/base_settings.py). Model construction settings are in `IntegratedModelSettings` ([core/model_settings.py](src/vimseo/core/model_settings.py)). Global configuration is in `src/vimseo/config/global_configuration.py` and loaded from environment variables via `pydantic-settings`.

### CLI entry points

| Command | Module |
|---|---|
| `dashboard_workflow` | `vimseo.dashboards.workflow.entry_point:main` |
| `workflow_executor` | `vimseo.workflow.workflow_executor:main` |
| `dashboard_mlflow` | `vimseo.storage_management.mlflow_ui_entry_point:main` |
| `visualize_analysis_node_result` | `vimseo.analysis_nodes.visualize_analysis_node_result:main` |

### Test structure

Tests mirror the source layout under `tests/`. Reference/mock problems used by tests live in `src/vimseo/problems/`. Test speed markers: `fast`, `medium_slow`, `slow`, `very_slow`. The default `tox`/`pytest` run excludes `slow` and `very_slow` tests.

### Changelog

Whenever a change adds, removes, renames, or changes the signature of a class, method,
function, or attribute of `src/vimseo/` that has no leading `_` (i.e. a change to the
public API), add a file to `changelog/fragments/` **before** considering the task
done -- see [`changelog/fragments/README.md`](changelog/fragments/README.md) for the
naming convention (`+<slug>.<type>.md`; a file named only by its type, e.g.
`changed.md`, is silently dropped by towncrier) and the valid types (`added`,
`changed`, `deprecated`, `removed`, `fixed`, `security`). This applies to an agent's
own changes exactly as it does to a human contributor's: do not wait to be asked.
A pull request that touches the public API without such a fragment fails CI
(`.github/workflows/python-package.yml`).
