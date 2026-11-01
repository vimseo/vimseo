<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

Restricted to `_protected` several members of the verification and surrogate analysis node
families, and of `PostProcessor`, that had no usage outside the analysis node itself (verified
against `vimseo-abaqus`, `vimseo-airframe`, `vimseo-composites`, `vimseo-dashboards`,
and the VTT GUI adapter):

- `BaseVerification`: `get_extended_output_names`, and the module functions
  `comparison_renaming`, `prepare_overall_dataset` of
  `vimseo.analysis_nodes.verification.base_verification`. The dead module function
  `convergence_renaming` was removed, as was the stale `metric_names` class
  annotation (the real storage is `self.options["metric_names"]`).
- `SurrogateAnalysisNode`: `quality`, `compute_selection_qualities`.
- `SensitivityAnalysisNode`: removed the dead `sensitivity_plot_factory` attribute and the
  dead `get_available_sensitivity_analyses` passthrough.
- `PostProcessor.plot_output_data` (the `evaluate_modulus_10_50` and
  `evaluate_modulus_e005_e025` methods of the same class were also considered, but
  are genuinely used by `vimseo-abaqus` and stay public).
- Fixed the stale `results` class annotations of `SensitivityAnalysisNode`, `SurrogateAnalysisNode`
  and `BaseVerification` (the real attribute is singular, `result`).

Also aligned `PreRunPostModel.set_n_cpus`, already treated as dead by its own
docstring, with the formal `DeprecationWarning` used by `BaseAnalysisNode.plot_results`,
instead of only a log warning.
