<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

The command `dashboard_results`, formerly provided by the plugin `vimseo-dashboards`, is now part of VIMSEO and requires the `dashboard` extra (`pip install "vimseo[dashboard]"`, plus the `mlflow` extra to explore an MLflow archive). Its pages are **Analysis Node Results** (any analysis node result, loaded from a file, an archive or a URI, with a specific view for a validation case), **Parameter Space** (the edition of a parameter space) and **Model Results** (the model results of an archive, refined by study, model, load case, status or query). The package `vimseo_dashboards` becomes `vimseo.dashboards`: its modules `analysis_node_result`, `model_results`, `space`, `validation` and `main_dashboard` keep their names, while `vimseo_dashboards.lib.result_loader`, `result_view`, `sidebar` and `utils` move to `vimseo.dashboards.visualisation`, and `vimseo_dashboards.lib.generic_layout` and `identity` are replaced by those of `vimseo.dashboards.visualisation`. Uninstall `vimseo-dashboards` (`pip uninstall vimseo-dashboards`) so that two commands `dashboard_results` do not conflict.
