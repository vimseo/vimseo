# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS -
#        :author: Jorge CAMACHO-CASERO
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
#        :author: benedicte REINE
"""
Manage model results
====================

Manage model results using several result managers.
"""

from __future__ import annotations

import logging

import mlflow
from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.bars import BarPlot
from mlflow import delete_run
from numpy import atleast_1d
from pandas import DataFrame
from pandas import concat

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_result import ModelResult
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.utilities.plotting_utils import plot_curves

activate_logger(level=logging.INFO)

# %%
# Properly storing model results when running hundreds of simulations with possibly several users and several studies
# at the same time is a key aspect, especially if model credibility demonstration is targeted.
# Our strategy is to separate the following concepts:
#  - scratch results: these are specific to models relying on external solvers. A scratch directory contains the data
#    read or written by the solver.
#  - archive results: these are the data we want to keep after the simulation. They comprise the input and output data,
#    metadata and files generated in the scratch directory that we want to conserve.
#  - a cache: while a cache could be seen as a way of archiving results, we prefer to separate cache and archiving.
#    However, a bridge is available between both: a cache can be generated from an archive or part of an archive.
#
# An archive manager can be chosen among ``DirectoryArchive`` or ``MlflowArchive``.
# In the first case, an arborescence of directories is generated under a directory ``default_archive``
# created in the current working directory.
# In the second case, an MLflow database is created.
# By default the database is file-based and is created under a directory ``mlflow_archive``
# in the current working directory.
# The root directory of the archive can be specified with argument ``directory_archive_root``
# passed to the constructor of the model or to ``create_model()``.
#
# The scratch results are stored in an arborescence of directories similarly to a ``DirectoryArchive``.
#
# The persistency policy of the scratch and the archive can be specified independently.
#
# By default, the storage generates unique directories at each new model execution.
# For a ``DirectoryArchive``, the argument ``job_name`` allows to store the result in a specific directory
# without creating unique directories.
#
# Here, a model is created with the default ``DirectoryArchive`` manager, and a specific job directory is used to
# store the archive result. The ``_accept_overwrite_job_dir`` attribute must be explicitly set to ``True``.
# The ``MockModelPersistent`` model has the specificity of requiring to store some generated files to the archive.
# The archive manager automatically handles the copy of these files from the scratch to the archive.
# Here, the scratch directories are kept such that the user can look into them:
model_name = "MockModelPersistent"
load_case = "LC1"
model = create_model(
    model_name,
    load_case,
    IntegratedModelSettings(
        directory_scratch_persistency=PersistencyPolicy.DELETE_NEVER,
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/visualize_model_result",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/visualize_model_result",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/visualize_model_result/{model_name}_{load_case}_cache.hdf",
    ),
)
model.archive_manager._accept_overwrite_job_dir = True
model.cache = None

# %%
# An execution is then performed. A ``JSON`` file is written in the directory ``my_experiment`` of the archive.
# It contains the input data, output data and metadata.
# Two files identified at model-level as being persistent have also been copied from the scratch to the archive.
model.execute({"x1": atleast_1d(2.0), "x2": atleast_1d(-2.0)})

# %%
# It often occurs that a cache becomes unusable due to:
#  - a change of VIMSEO version, altering the input, output or metadata of a model,
#  - a mix of successful and failed simulations (by fail, we mean that models may be fault tolerant and
#    outputs NaNs in the output data in case of errors). In general, we want to filter out failed runs.
#  - a large number of results, and for part of them, we have no traceability about and we do not trust the
#    results.
# Then, a useful feature is to generate a cache file from an archive.
# ``create_cache_from_archive()`` generates a cache file with same name as the current cache suffixed by '_from_archive'.
# For a ``DirectoryArchive``, the whole archive is considered (no filtering possible):
cache_from_archive = model.create_cache_from_archive()
print(cache_from_archive)

# %%
# An archive storage based on [MLflow](https://mlflow.org) is also available.
# MLflow stores the runs by so-called 'Experiments'.
# The default experiment name is ``{model_name}_{load_case}``.
# Again, we create a model instance:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/mlflow_archive/visualize_model_result",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/visualize_model_result",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/visualize_model_result/{model_name}_{load_case}_cache.hdf",
        archive_manager="MlflowArchive",
    ),
)
model.cache = None

# %%
# All runs for the default and specific (specified below as ``my_experiment``) experiment name
# are first deleted:
runs = mlflow.search_runs(
    experiment_names=["BendingTestAnalytical_Cantilever", "my_experiment"]
)
for id in runs["run_id"]:
    delete_run(id)

# A first execution is done. Its result is stored under the default experiment name,
# which is ``{model_name}_{load_case}``:
model.execute({"height": atleast_1d(40.0)})

# %%
# Then, another experiment is defined.
# It can be useful to group runs for a given study.
# The model is then executed for two different beam height:
model.archive_manager.set_experiment("my_experiment")
model.execute({"height": atleast_1d(50.0)})
model.execute({"height": atleast_1d(60.0)})

# %%
# The archive results can be visualized through the MLflow User Interface.
# The ``uri`` of the MLflow database must be specified to the UI:
#  - For exemple, Under Windows:
#    ``mlflow ui --backend-store-uri file:\\\\\\C:\\Users\\sebastien.bocquet\\PycharmProjects\\vimseo\\tests\\storage_management\\my_experiment``
#  - Or under Linux:
#    ``mlflow ui --backend-store-uri file:////home/sebastien.bocquet/PycharmProjects/vims_only/doc_src/_examples/02-integrated_models/mlflow_archive``
# The uri can be retrieved with ``model._storage_manager.uri``.
#
# The mapping from model raw results (input, output, metadata) and MLflow result tracking framework is done as follows:
#  - all numbers among the input and output data (including arrays of size one, from which the number is extracted),
#    are stored as MLflow ``metrics``. Inputs are distinguished by prefixing their name by ``inputs.``,
#  - all other type of data among the input and output data are considered as MLflow ``params``. They are jsonified
#    and stored as strings,
#  - the metadata are stored as MLflow ``tags``.
# The UI segregates the runs by experiment, and provides a
# [searching functionality](https://mlflow.org/docs/latest/ml/search/search-runs/).
# MLflow is compatible with several databases (remote PostgreSql, Amazon S3 etc...),
# allowing the archive storage to scale (company level or project level).

# %%
# Runs can also be searched programmatically, here by experiment and for a given input range.
runs = mlflow.search_runs(
    experiment_names=["my_experiment"],
    filter_string="metrics.inputs.height > 50.0",
)
assert len(runs) == 1
runs

# %%
# Metadata could also be used in the query, for instance ``tags.user = "a_user"``.
# Note that the result returned by ``get_result()`` has the following format:
# ``{"inputs": input_data, "output": output_data}``.
archive_result = model.archive_manager.get_result(runs["run_id"][0])
archive_result

# %%
# It can be converted to a user-friendly result format [ModelResult][vimseo.core.model_result.ModelResult]
# that can be easily visualized and compared:
result = ModelResult.from_data(archive_result)
result

# %%
# We perform another query to retrieve the second run:
runs = mlflow.search_runs(
    experiment_names=["my_experiment"],
    filter_string="metrics.inputs.height <= 51.0 AND metrics.inputs.height >= 49.0",
)
assert len(runs) == 1
archive_result_1 = model.archive_manager.get_result(runs["run_id"][0])
result_1 = ModelResult.from_data(archive_result_1)
result_1

# %%
# It is possible to create a cache file from the archive.
# By default, the runs of the current experiment are considered.
# Since experiment "my_experiment" has two runs, we expect the created cache to have two entries:
cache_from_archive = model.create_cache_from_archive()
print(cache_from_archive)


# %%
# The displacement curves of both results can be compared.They are identical for this displacement-imposed loading:
plot_curves(
    [
        result.get_curve(("dplt_grid", "dplt")),
        result_1.get_curve(("dplt_grid", "dplt")),
    ],
    labels=["result", "result 1"],
    save=False,
    show=True,
)

# %%
# However the resistance force at beam end are different:
variable_names = ["height", "reaction_forces"]
df = concat(
    [
        DataFrame([result.get_numeric_scalars(variable_names=variable_names)]),
        DataFrame([result_1.get_numeric_scalars(variable_names=variable_names)]),
    ],
    ignore_index=True,
)
plot = BarPlot(Dataset.from_dataframe(df))
plot.title = "Comparison of model result with data"
plot.font_size = 20
plot.labels = ["height 50mm", "height 60mm"]
fig = plot.execute(save=False, show=True, file_format="html")[0]
fig
