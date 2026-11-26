<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

Each execution of an analysis node fills a new `result`: a result returned by a previous execution, e.g. a DOE result passed to a sensitivity analysis, is no longer overwritten, nor given the `analysis_node_run_id` of the next run. The result of `DesignValueAnalysisNode` is a `DesignValueResult` holding a copy of the statistics, no longer the result of its `StatisticsAnalysisNode`.
