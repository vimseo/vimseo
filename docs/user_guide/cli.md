<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Command line interface

The following commands can be run in a terminal:

| command line | what it does|
| --- | --- |
| ``dashboard_workflow``    | Opens a dashboard to prepare a workflow |
| ``workflow_executor``    |  Runs a workflow (exported as a ``JSON`` file) |
| ``dashboard_mlflow``    | Opens the ``MLflow`` interface to explore the stored experiments |
| ``visualize_analysis_node_result``    | Writes the figures, the tables and the metadata of analysis node results in a directory, from their URIs (result file, analysis node run directory, ``analysis-node-run:{analysis_node_run_id}`` or ``runs:/{mlflow_run_id}``) |

The package [vimseo-dashboards](https://forge-is.pf.irt-saintexupery.com/vims/vimseo-dashboards) adds
``dashboard_results``, which explores any analysis node result loaded from a file, an archive
or a URI (with a specific view for a validation case), edits a parameter space, and
explores the model results of an archive (``DirectoryArchive`` or ``MlflowArchive``):
every result is listed, then refined by study, model, load case, status or query.
