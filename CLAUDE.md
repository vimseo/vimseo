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

**Install (editable, with dev dependencies):**
```bash
uv pip install -e ".[dev]"
# or via tox:
tox -e py312 -- --co  # list tests without running
```

**Run tests (fast tests only, default):**
```bash
pytest
# or via tox:
tox -e py312
```

**Run a single test file:**
```bash
pytest tests/tools/test_doe.py
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

VIMSEO is a VV&UQ (Verification, Validation & Uncertainty Quantification) framework. It wraps simulation models and provides analysis tools to assess simulation credibility. The library is built on top of [GEMSEO](https://gemseo.readthedocs.io/), a Python MDO library — VIMSEO models are GEMSEO `Discipline` subclasses.

### Model layer (`src/vimseo/core/`)

`IntegratedModel` ([base_integrated_model.py](src/vimseo/core/base_integrated_model.py)) is the central abstraction. It is a GEMSEO `Discipline` that wraps one or more `BaseComponent` objects representing model execution stages. Two concrete model base classes exist:

- **`PreRunPostModel`** ([pre_run_post_model.py](src/vimseo/core/pre_run_post_model.py)): Chains a pre-processor, run-processor, and post-processor. Component class names follow the convention `{Family}_{LoadCase}` (e.g., `PreStraightBeam_Cantilever`). This is why the ruff `N801` rule (CapWords) is disabled.
- **`BaseDisciplineModel`** ([base_discipline_model.py](src/vimseo/core/base_discipline_model.py)): Wraps a single GEMSEO `Discipline` directly.

A `LoadCase` encapsulates the boundary conditions and parameters for a model run. Models are discovered via `ModelFactory` (GEMSEO plugin mechanism, registered via the `gemseo_plugins` entry point in `pyproject.toml`).

### Tools layer (`src/vimseo/tools/`)

All analysis tools inherit from `BaseTool` ([base_tool.py](src/vimseo/tools/base_tool.py)). The tool pattern:

- Class attributes `_INPUTS` (a `BaseInputs` subclass) and `_SETTINGS` (a `BaseSettings` subclass) define Pydantic models for validation.
- `execute(inputs=..., settings=...)` accepts instances of those Pydantic models, or falls back to keyword arguments.
- Results are stored in `tool.result` (a `BaseResult` subclass) and persisted via `tool.save_results()` to HDF5/pickle.
- `plot_results(result, ...)` produces Plotly figures.

Available tool categories: DOE, sensitivity analysis, calibration, verification (solution + vs-data + vs-model), validation (point + case), surrogate modelling, statistics, Bayesian analysis, design value.

### Storage (`src/vimseo/storage_management/`)

`IntegratedModelSettings.archive_manager` selects the storage backend:
- `"MlflowArchive"` — stores model runs in an MLflow tracking server (default for users).
- `"DirectoryArchive"` — stores results in a local directory structure.
- `"ScratchArchive"` — temporary storage.

### Workflow engine (`src/vimseo/workflow/`)

`Workflow` ([workflow.py](src/vimseo/workflow/workflow.py)) chains tools using GEMSEO's `MDAChain`. Workflows can be serialised to/from JSON and executed via the `workflow_executor` CLI entry point. The `dashboard_workflow` Streamlit app lets users build workflows interactively.

### Settings / configuration

All settings classes inherit from `BaseSettings` (Pydantic `BaseModel` with `extra="forbid"`) in [tools/base_settings.py](src/vimseo/tools/base_settings.py). Model construction settings are in `IntegratedModelSettings` ([core/model_settings.py](src/vimseo/core/model_settings.py)). Global configuration is in `src/vimseo/config/global_configuration.py` and loaded from environment variables via `pydantic-settings`.

### CLI entry points

| Command | Module |
|---|---|
| `dashboard_workflow` | `vimseo.dashboards.workflow.entry_point:main` |
| `workflow_executor` | `vimseo.workflow.workflow_executor:main` |
| `dashboard_database_viewer` | `vimseo.dashboards.database_viewer.db_viewer_entry_point:main` |
| `dashboard_mlflow` | `vimseo.storage_management.mlflow_ui_entry_point:main` |

### Test structure

Tests mirror the source layout under `tests/`. Reference/mock problems used by tests live in `src/vimseo/problems/`. Test speed markers: `fast`, `medium_slow`, `slow`, `very_slow`. The default `tox`/`pytest` run excludes `slow` and `very_slow` tests.
