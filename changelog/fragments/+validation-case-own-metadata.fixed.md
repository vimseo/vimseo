<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

`ValidationCaseResult.set_from_point_results` gives the case its own metadata, with a new `analysis_node_run_id`, its points as `child_analysis_node_run_ids` and their simulations as `simulation_run_ids`, instead of sharing the metadata object of its first point.
