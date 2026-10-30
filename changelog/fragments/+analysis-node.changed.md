<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

**Breaking change:** the "tool" concept is renamed "analysis node", without
deprecation aliases:

- The package `vimseo.tools` is now `vimseo.analysis_nodes`, and its modules follow
  (`base_tool` → `base_analysis_node`, `post_tools` → `post_analysis_nodes`,
  `tools_factory` → `analysis_nodes_factory`, ...).
  `vimseo.storage_management.tool_archive` is now
  `vimseo.storage_management.analysis_node_archive`.
- The classes ending with `Tool` now end with `AnalysisNode` (`BaseTool` →
  `BaseAnalysisNode`, `DOETool` → `DOEAnalysisNode`, `SpaceToolResult` →
  `SpaceAnalysisNodeResult`, `DirectoryToolArchive` → `DirectoryAnalysisNodeArchive`,
  ...). `BaseAnalysisTool` is removed: the analyses derive from
  `BaseCompositeAnalysisNode`. `ToolsFactory` is now `AnalysisNodesFactory` and
  `AnalysisToolsFactory` is now `CompositeAnalysisNodesFactory`.
- The functions, methods, arguments and settings containing `tool` now contain
  `analysis_node`, e.g. `load_tool_results` → `load_analysis_node_results`,
  `search_tool_runs` → `search_analysis_node_runs`, `subtools` →
  `sub_analysis_nodes`, `tool_run_id` → `analysis_node_run_id`, and the setting
  `tool_archive_manager` (`VIMSEO_TOOL_ARCHIVE_MANAGER`) →
  `analysis_node_archive_manager` (`VIMSEO_ANALYSIS_NODE_ARCHIVE_MANAGER`).
- The command `visualize_tool_result` is now `visualize_analysis_node_result`.
- The archives use the new names: the directory `{study}/tools/` is now
  `{study}/analysis_nodes/`, the MLflow run kind `tool_run` is now
  `analysis_node_run`, the tags `vimseo.tool_*` are now `vimseo.analysis_node_*`, the
  URI scheme `tool-run:` is now `analysis-node-run:` and the metadata field
  `tool_run_id` is now `analysis_node_run_id`. The archives of tool runs written by a
  previous version can no longer be read.

To adapt, replace `tool` by `analysis_node` and `Tool` by `AnalysisNode` in the
imports and the names, and archive the analyses again.
