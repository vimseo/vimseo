<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

Restricted to `_protected` several more members with no usage outside the analysis node
itself (verified against `vimseo-abaqus`, `vimseo-airframe`, `vimseo-composites`,
`vimseo-dashboards`, and the VTT GUI adapter):

- `StatisticsAnalysisNode`: `build_distributions`, `get_criteria`, `get_fitting_matrix`,
  `get_available_distributions`, `get_available_criteria`, `get_significance_tests`,
  `compute_all_statistics` (these were thin static passthroughs to
  `ParametricStatistics`, or an internal helper, never called on a `StatisticsAnalysisNode`
  instance from outside the class -- `compute_ecdf`, directly used by the tests,
  stays public).
- `BayesAnalysisNode`: `log_posterior`, `sampling`. Also removed the stale `data` class
  annotation, which never matched a real attribute (the real one is `_data`).
  `cropping`, `build_posterior_predictive`, `marginal_likelihood`, `lppd` and `post`
  were also considered, but are each directly exercised standalone by the test suite
  and/or the documentation gallery, so they stay public.
- `CalibrationStep`: `get_metric_curve_names`, `get_metric_scalar_names` (thin
  wrappers of the module functions of the same name in `calibration_step_result.py`,
  which stay public).
- `SpaceBuilder` (`vimseo.analysis_nodes.lib.space_builders`): removed the dead
  `get_builder_options`, and renamed `filter_options` (already marked for removal by
  a `# TODO` in its own file) to `_filter_options`. `get_available_distributions`,
  `grammar_names`, `build` and `SpaceAnalysisNode.get_available_space_builders` were also
  considered, but are genuinely used by the documentation gallery, the tests, and/or
  `vimseo-dashboards`/the VTT GUI adapter, so they stay public.
- `ValidationPointResult.get_output_names` and `ValidationCaseResult.get_common_values`
  / `add_averaged_point`: each only called from another method of the same result
  class (`_create_figures` or `set_from_point_results`, both of which stay public).

The `doe`, `design_value`, and `validation`/`validation_case` analysis node classes themselves
were also audited, but had no candidate beyond the stale `results` class annotations
already covered by the base `BaseAnalysisNode` fix.
