<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

Renamed several `BaseAnalysisNode` members that had no real usage outside the analysis node framework
itself (verified against `vimseo-abaqus`, `vimseo-airframe`, `vimseo-composites`,
`vimseo-dashboards`, and the VTT GUI adapter) to be `_protected`:
`validate` (and `BaseCompositeAnalysisNode.validate`), `report_name`, `time`, `option_names`,
`grammar`, `settings_names`, `settings`. Also renamed the `BaseAnalysisNode.results` class
annotation, which never matched a real attribute (the actual one is `result`,
singular), to `result`.

Renamed four module-level helpers of `vimseo.analysis_nodes.result_visualization` that are
only used within that module to be `_protected`: `is_scalar`, `value_to_dataframe`,
`get_number`, `is_matplotlib_figure`.
