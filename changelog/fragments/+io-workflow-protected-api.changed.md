<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

Continued the public-API restriction pass on `analysis_nodes/io/` and `workflow/`:

- Fixed the stale `results` class annotations on the file readers of
  `vimseo.analysis_nodes.io` (`ReaderFileDataFrame`, `ReaderFileGemseoDataset`, `ReaderFileTecplot`,
  `MaterialReader`, `ParameterSpaceReader`): the real attribute is singular, `result`,
  and in one case (`ReaderFileGemseoDataset`) the annotated type itself was wrong
  (`IODataset` instead of `DatasetResult`).
- `vimseo.workflow.workflow_step`: renamed `deserialize_pydantic_settings`,
  `serialize_pydantic_settings` and `create_pydantic_model` to `_protected`, as they
  are only used within this module. `get_pydantic_model_item`, used directly by
  `vimseo.dashboards.workflow.dashboard_workflow_model`, stays public, as does
  everything else on `Workflow`/`WorkflowStep` (all exercised directly by
  `tests/workflow/`).

`storage_management/` (archive and scratch managers, excluding `analysis_node_archive/`
already audited) was also reviewed: its public surface is a cross-module contract
between `IntegratedModel` and the `DirectoryArchive`/`MlflowArchive`/`DirectoryScratch`
backends, and every member is either an abstract interface method or directly tested
-- no change needed there.
