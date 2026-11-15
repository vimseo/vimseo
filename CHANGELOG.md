

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

<!-- towncrier release notes start -->

# Unreleased

## Added

- Archive of the results of the tools. Each time a tool is executed, its result is
  written under `{directory_archive_root}/tools/{tool_name}/{tool_run_id}/`
  (`{tool_name}_result.hdf5`, named as by `save_results()`, and
  `{tool_name}_result_metadata.json`, a readable summary with the status of the run,
  its settings and the identifiers of its simulations and of its parent and child
  tool runs). The
  archive is searched with `DirectoryToolArchive.search_tool_runs()`, a result is read
  back with `get_tool_result()`, and `find_tool_runs_of_simulation()` gives the tool
  runs which used a simulation. It is enabled by default with the archive manager of
  the simulations (`DirectoryArchive`), in `default_archive/`. It is configured
  by the `archive_manager` and `directory_archive_root` arguments of any tool (the
  settings of `ArchiveLocationSettings`, shared with the models), or by
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
- `PostProcessor.POSTPROCESS_DESPITE_FAULTY_RUN`: a post-processor can opt in to
  postprocess a faulty run, provided that `_can_postprocess()` finds what it needs
  in the job directory.
- `solver_utilities.evaluate_modulus_10_50()` (strain- or stress-based interval)
  and `solver_utilities.evaluate_modulus_e005_e025()`.

## Changed

- The results are loaded by `vimseo.api.load_model_results(refs)` and
  `load_tool_results(refs)`, which take one reference or many (an identifier,
  `run:{run_id}` / `tool-run:{tool_run_id}`, a path, `runs:/{mlflow_run_id}`) and always
  return a collection, `ModelResults` or `ToolResults`. `load_simulation_results` is
  and `vimseo.api.load_tool_result` are removed, use `load_tool_results(ref)[0]`.
  `search_model_results` and
  `search_tool_runs` list the runs from their summaries, and accept a `query` written
  as for `pandas.DataFrame.query`, with `or`. `open_model_results` and
  `open_tool_results` open a whole archive as a collection, explored with `filter`,
  `ignoring`, `varying_inputs`, `families(along=...)`, `duplicates`, `to_dataframe`,
  `to_dataset` and `visualize`. The collection of the results of a single tool keeps
  only the inputs and outputs of this tool, and `to_dataframe` keeps the prefixes
  `inputs.` / `outputs.` of an input and an output with the same name, e.g. the
  setting and the key value `n_samples` of a DOE. The resolvers of
  `storage_management.tool_archive.uri` take their archive settings as keyword
  arguments only.
- `ModelResult` is structured: `scalars` and `vectors` are mappings which can be called
  to select variables by name, type and group (`scalars(group="inputs")`); `curves` and
  `plots` are lists which can also be indexed by name (`curves["dplt_vs_dplt_grid"]`);
  `run_id`, `study_name`, `model_name`, `load_case`, `status` and `tool_run_id` are
  properties; `from_dict()` and `to_dict()` convert from and to the raw data, and it is
  plotted without its model by `plot()`. Breaking: `from_data`, `get_curve` and
  `get_numeric_scalars` are removed, use `from_dict()`, `curves["{y}_vs_{x}"]` and
  `scalars(variable_names)`. A `Plot` may have a `name`.
- The default scatter matrix of a DOE leaves out the variables which do not vary.
- The parametric study of a DOE is drawn per family of samples differing by the
  abscissa only: when several inputs vary, the scalar outputs are drawn with a line
  per family (or in a figure per family, `family_layout="one_figure_per_family"`) and
  the curves in a figure per family, suffixed by the values of the other inputs, e.g.
  `[width=20.0]`. The samples belonging to no family, e.g. all the samples of a LHS,
  are left out with a warning, and `get_plot_choices()` proposes as abscissa only the
  inputs forming families. Without abscissa, the curves of the samples are labelled
  by their varying inputs.
- The examples of `02_integrated_models/plot_03_model_result_management.py` and
  `13_tool_result_management/` are replaced by the gallery `14_data_management`.
- The simulations and the tool runs are grouped by **study**, `study_name`, a setting
  of the models and of the tools (default `default_study`, `VIMSEO_STUDY_NAME`). A
  `DirectoryArchive` stores a simulation in `{root}/{study}/{model}/{load_case}/{run_id}/`
  and a tool run in `{root}/{study}/tools/{tool_name}/{tool_run_id}/`; an
  `MlflowArchive` stores both in the experiment `{study}`, told apart by the tag
  `vimseo.kind`. The searches by identifier look into every study. Breaking:
  `set_experiment()`, `experiment_name` and `VIMSEO_DATABASE__EXPERIMENT_NAME` are
  removed, use `set_study_name()` and `VIMSEO_STUDY_NAME`; the archives written with
  the former layout are no longer read by `get_archived_results()` and
  `search_tool_runs()` (they stay readable by path and by `run_id`).
- The identifiers `run_id` and `tool_run_id` are time ordered,
  `{YYYYMMDDTHHMMSS}_{8 hexadecimal characters}` (UTC), and a job directory is named
  by the `run_id` of its simulation instead of `1`, `2`... A simulation has a `status`
  metadata, `RUNNING`, `FINISHED` or `FAILED`: its inputs are archived with
  `RUNNING` when it starts, so that a crashed simulation stays visible. The figures
  saved by `plot_results()` in the job directory are no longer prefixed by the names
  of the model and of the load case, to keep the paths short on Windows.
  The outputs of a model hold the new metadata `run_id`, `tool_run_id`, `study_name`
  and `status`: a cache file written by a former version lacks them, and an execution
  served by it fails with `Missing required names`; delete such cache files (or give
  the model a new `cache_file_path`).
- Breaking: the command `dashboard_database_viewer` is removed, as the dashboards
  exploring results live in the package
  [vimseo-dashboards](https://forge-is.pf.irt-saintexupery.com/vims/vimseo-dashboards): use the page
  **Model Results** of its command `dashboard_results`. It lists every model result of
  the archive, whatever its study, model and load case, and refines them by study,
  model, load case, status and query; it no longer instantiates the models.
- `ModelResults.visualize()` warns about the figures it does not draw because some results
  do not have them.
- With an `MlflowArchive` in `Team` mode, `directory_archive_root` is ignored, with a
  warning; in `Local` mode, it is the directory of the database and wins over
  `local_uri`.
- The figures and the tables of a result are obtained with `result.plot()` and
  `result.to_dataframes()`. Breaking: `visualize()`, `tabulate()`,
  `get_visualization_settings()`, `get_visualization_choices()` and
  `BaseVisualizationSettings` are renamed, without alias, `plot()`,
  `to_dataframes()`, `get_plot_settings()`, `get_plot_choices()` and
  `BasePlotSettings`; `BaseTool.plot_results()` is removed, use
  `tool.result.plot()`. Every tool result whose plot settings select names gives
  them by `get_plot_choices()`. A result class declares its settings in
  `_PLOT_SETTINGS` (formerly `_VISUALIZATION_SETTINGS`). The parametric study of a DOE is
  drawn by `plot_family`, shared with the families of results.
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
- `SensitivityTool.plot_results()` and `OATSensitivityTool.plot_results()` are
  removed, like `BaseTool.plot_results()`: the figures of a sensitivity analysis
  are drawn by `SensitivityResult.plot()`, and the tornado diagrams of a star OAT
  analysis by `OATSensitivityResult.plot()`, which also gives its plot choices,
  its tables of indices and its key values.
- The documentation is versioned: each release is published under its version
  (`https://vimseo.github.io/vimseo/0.1.7/`), the last one also under `latest`, and
  `main` under `develop`. The links of the README to the documentation point to
  `latest`; the deep links to the unversioned documentation are broken.
- `PostProcessor._run` is now generic: it handles the faulty-run logic from the
  `_is_run_faulty()` and `_can_postprocess()` hooks, and delegates the actual
  postprocessing to `_postprocess()`, which subclasses implement instead of `_run`.
- `PostProcessor.evaluate_modulus_10_50()` and `evaluate_modulus_e005_e025()` are
  removed, use their `solver_utilities` counterparts. The `Modulus1050` and
  `ModulusE005E025` direct measures use them too.

## Fixed

- The scatter matrix of a code verification, against data or against a model,
  showed the inputs only: it now shows the scalar errors versus the inputs, also when
  a single input varies. Breaking: its figure `input_scatter_matrix_{metric}` is
  renamed `errors_vs_inputs_{metric}`.
- A solution verification executed from data, without model, was not archived.
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

# Version 0.1.7 (10/12/2026)

## Added

- Run limits of the jobs, as user job options of every job executor:
  `solver_time_limit` (the maximum solver time, counted from the first convergence
  file written, so that a wait in a licence queue does not count) and `deadline` (a
  wall-clock time). A job reaching a limit is terminated (`abaqus terminate` for
  Abaqus, SIGTERM to the process group by default), its results so far are kept and
  the run is reported as faulty; `JobExecutor.stopped_by` tells which limit stopped it.
- Tools accept the data users already have: a mapping of variable names to values,
  a nested `{"inputs": ..., "outputs": ...}` mapping, a mono-index `DataFrame`, the
  legacy `name{group}[component]` `DataFrame` or a `Dataset`
  (`vimseo.utilities.datasets.to_dataset`, `resolve_io_groups`, `DatasetInput`).
  Input and output groups are resolved from explicit names or the model grammars.
  `StochasticValidationPointSettings.input_names` (#91).
- Models and load cases declare their figures with `PLOTS`: a tuple of variable names
  (abscissa then ordinates) or a `Plot` with several styled lines, a secondary
  ordinate axis, horizontal reference lines and an `x_label`. A load case `PLOTS`
  entry overrides the model one with the same abscissa and first ordinate, or adds
  a figure. Figures are rendered with Plotly. `ModelResult.plots` groups the curves
  per figure (`CurveSet`) (#107).
- `TanOpenHole`, an open-hole tension model (Tan), with utilities to extract lines
  from a field (#18).
- Optional extras `dashboard`, `mlflow`, `mesh`, `jax` and `all`: the mandatory
  dependencies only build, execute and serialize a model, so VIMSEO installs on a
  machine without graphical stack (HPC) (#18).
- `ReaderFileTecplot`, a reader of Tecplot ASCII files, with aliases of the
  coordinate variable names, and `FieldResult` (#64, #103).
- A model can be built with an alternative compatible material; material registry;
  `Ta6v_annealed` material.
- How-to page on configuring VIMSEO with `VIMSEO_*` environment variables or a
  `.env` file.

## Changed

- VIMSEO depends on the official `gemseo >= 6.3.3` and `gemseo-calibration >= 4.0.1`
  instead of the private forks `gemseo-vimseo` and `gemseo_calibration-vimseo`.
  Calibration follows the upstream renames: measures become metrics
  (`IntegratedMeasure` → `BaseIntegratedMetric`, `MeanMeasure` → `BaseMeanMetric`),
  settings `output`/`measure`/`mesh` → `output_name`/`metric_name`/`mesh_name`.
  The SBPISE curve-scaling settings move to `CalibrationMetricSettings`. The
  `ScatterMatrix` argument `coloring_variable` becomes `classifier` (#105).
- **Breaking:** the `CURVES` class attribute of the models is replaced by `PLOTS`; a
  model still declaring `CURVES` is rejected at import time. The per-load-case JSON
  file of `plot_parameters` is replaced by `LoadCase.PLOTS`; a stray JSON file next to
  a load case raises a `ValueError` (#107).
- **Breaking:** `plot_curves` is renamed `superpose_curves` (#107).
- The plots are no longer part of the load case and model descriptions; results
  saved with the former `plots` field still load (#107).
- Renamed the `TanOpenHole` model input `grid_size` to `grid_resolution` (number of
  grid points per direction), bounded to 5..1000 (#104).
- Mock models: `MockCurves` outputs `y_axis`/`y` → `x_history`/`y_history`;
  `MockMultiCurves` `critical_energy` → `critical_crack_position` (#107).
- The components are reorganized under `vimseo.core.components` (#58).
- The Streamlit dashboards move to `vimseo.dashboards`; the console scripts are
  updated (#56, #67).
- `api.create_model` merges `model_options` with keyword options (keyword wins)
  instead of rejecting the combination.

## Removed

- `vimseo.core.model_run_executor` and its unused entry point.
- The unfinished `MockModelLongRun` mock (#105).

## Fixed

- A model input silently rejected by the grammar and reverted to its default now
  raises a `ValueError` (#104).
- The `TanOpenHole` grid resolution was not applied (#104).
- The truncation bounds of the material properties are kept in the parameter space
  and its JSON serialization.
- The internal coupling variables of a `PreRunPostModel` are no longer archived, so
  `create_cache_from_archive` replays archived runs (#105).
- `JobExecutor` splits commands with `shlex`, keeping quoted arguments (#105).
- The external software subprocess is killed in every case (#52).
- `ReaderFileTecplot` reads every zone, not only the first one (#103).
- Conversion of a `DataFrame` to a `Dataset` in the database viewer (#67).
- Serialization roundtrip of pandas masked dtypes; Python 3.10 compatibility
  (`operator.call`); intermittent pydantic "not fully defined" errors (#105).
- Documentation: broken links, image paths, popups and crash of the doc build
  (#54, #62, #87).

# Version 0.1.6 (05/12/2026)

## Added

- Export to disk of analysis results (DOE, Sensitivity etc...) in hd5 format.

## Changed

- None

## Fixed

- None
