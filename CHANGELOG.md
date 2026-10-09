

<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

<!--
Changelog titles are:
- Added: for new features.
- Changed: for changes in existing functionality.
- Deprecated: for soon-to-be removed features.
- Removed: for now removed features.
- Fixed: for any bug fixes.
- Security: in case of vulnerabilities.
-->

# Changelog

All notable changes of this project will be documented here.

The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0)
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Version 0.1.6 (05/12/2026)

## Added

- Export to disk of analysis results (DOE, Sensitivity etc...) in hd5 format.
- Archive of the results of the tools. Each time a tool is executed, its result is
  written under `{archive_root}/tools/{tool_name}/{tool_run_id}/`
  (`{tool_name}_result.hdf5`, named as by `save_results()`, and
  `{tool_name}_result_metadata.json`, a readable summary with the status of the run,
  its settings and the identifiers of its simulations and of its parent and child
  tool runs). The
  archive is searched with `DirectoryToolArchive.search_tool_runs()`, a result is read
  back with `get_tool_result()`, and `find_tool_runs_of_simulation()` gives the tool
  runs which used a simulation. It is enabled by default with the archive manager of
  the simulations (`DirectoryArchive`), in `default_archive/`. It is configured
  by the `archive_manager` and `archive_root` arguments of any tool, or by
  `tool_archive_manager` in the configuration (`none` disables it). The subtools of
  a composite tool use its archive settings, unless they were given their own. A
  tool run which raised is archived with the status `FAILED`, and an error of the
  archive is logged without losing the result.
- Unique identifiers linking the simulations and the tool results. A simulation
  really run has a `run_id` metadata, and a `tool_run_id` metadata which is the
  run of the tool that executed it (empty otherwise). A tool result has
  `metadata.tool_run_id`, `metadata.parent_tool_run_id`, `metadata.child_tool_run_ids` and
  `metadata.simulation_run_ids`, the latter including the simulations retrieved from
  the model cache. A simulation retrieved from the cache keeps the identifiers of the
  run which created it. The simulations executed by a thread or a process pool
  started during a tool run are not recorded.

## Changed

- Renamed the `TanOpenHole` model input `grid_size` to `grid_resolution` (same
  meaning: number of grid points per direction) to remove the ambiguity with a
  grid spacing.
- `MlflowArchive` no longer calls `mlflow.set_tracking_uri()` and
  `mlflow.set_experiment()`: it queries the database with its own MLflow client,
  so that several archives with different uris can coexist in the same process.
  A script which uses the MLflow API directly (`mlflow.search_runs()`,
  `mlflow.delete_run()`...) must now call
  `mlflow.set_tracking_uri(model.archive_manager.uri)` first, otherwise it
  queries the default `./mlruns` database without any error.
- `MlflowArchive` creates the MLflow run when the job starts instead of when its
  results are published. Runs which are still running or failed are not returned
  by `get_archived_results()`.
- Renamed the `archive_manager` configuration setting (environment variable
  `VIMSEO_ARCHIVE_MANAGER`) to `run_archive_manager`
  (`VIMSEO_RUN_ARCHIVE_MANAGER`), to distinguish it from the new
  `tool_archive_manager`. No alias: `VIMSEO_ARCHIVE_MANAGER` left in a `.env`
  file now makes `VimseoSettings()` fail at startup with a
  `pydantic.ValidationError` naming the offending key (an unknown key set as a
  plain environment variable is still ignored, but a `.env` file is validated
  strictly). Update any `.env` file accordingly. This does not affect the
  `archive_manager` argument of a model or a tool, nor the `model.archive_manager`
  property, which are unrelated to this configuration setting.

## Fixed

- `DeterministicValidationCase` executed the model directly instead of its
  `CustomDOETool` subtool, whose result was therefore empty. The subtool now
  simulates the samples, once per cache file, and holds all of them.
- A `DataFrame` with a `RangeIndex` (a DOE dataset for instance) was read back from
  an HDF5 result with an `Index` of integers, which is a different type.
- The `directory_archive_job` metadata was empty in the outputs and in the cache of
  a model archived with `MlflowArchive`, and an invalid path on Windows.
- A persistency policy deleting the job with `MlflowArchive` deleted the previous
  run instead of the current one.
- A model whose job raised left its `MlflowArchive` run in the running state; it is
  now marked as failed.
- Two `MlflowArchive` with different uris in the same process disturbed each other.
