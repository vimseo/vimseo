<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Data management

Every result of VIMSEO goes through the same roundtrip: **generate**, **save**,
**load**, **plot**. It reads the same for the results of a model and the results of a
analysis node, and for the two archives, `DirectoryArchive` and `MlflowArchive`.

Reading path:

1. `plot_01_roundtrip`: the whole roundtrip in a few lines, and the table of the API.
2. One example per API method, for both kinds of results:
   `plot_02_save_and_find`, `plot_03_load`, `plot_04_visualize`.
3. The details of each archive, for each kind of result:
   `plot_05_model_results_in_directories`, `plot_06_model_results_in_mlflow`,
   `plot_07_analysis_node_results_in_directories`, `plot_08_analysis_node_results_in_mlflow`.
4. Explore a set of results: `plot_09_explore_results`.
