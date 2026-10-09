# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import annotations

from copy import deepcopy

import pytest
from numpy.core.shape_base import atleast_1d
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.storage_management.base_storage_manager import PersistencyPolicy

# The MlflowArchive backend is shipped by the "mlflow" extra.
mlflow = pytest.importorskip("mlflow")


def test_result_decoding(tmp_wd):
    """Check that a mlflow run data is correctly converted as a model result."""
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(
            archive_manager="MlflowArchive",
        ),
    )
    model.cache = None

    model.execute({"x1": atleast_1d(1.0), "x2": atleast_1d(2.0)})
    model_result = model.archive_manager.get_result()

    for name in model.get_input_data_names():
        assert_array_equal(model.get_input_data()[name], model_result["inputs"][name])
    for name in model.get_output_data_names():
        assert_array_equal(model.get_output_data()[name], model_result["outputs"][name])


def test_cache_from_archive(tmp_wd):
    """Check that the model cache can be set from an archive.

    Also check that the cache from archive is equal to the current model cache.
    """
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.execute()
    saved_cache = deepcopy(model.cache)
    model.create_cache_from_archive(run_ids=[model.archive_manager._current_run_id])

    expected_dataset = saved_cache.to_dataset(categorize=False).to_dict_of_arrays(
        by_group=False
    )
    dataset = model.cache.to_dataset(categorize=False).to_dict_of_arrays(by_group=False)
    tested_names = [
        name
        for name in expected_dataset
        if name not in [MetaDataNames.date, MetaDataNames.cpu_time]
    ]
    for name in tested_names:
        assert_array_equal(expected_dataset[name], dataset[name])

    # Check that we pass in the cache if the model is re-executed: the number of
    # archived result should remain equal to one:
    model.execute()
    assert len(model.archive_manager.get_archived_results()) == 1


def test_copy_persistent_files(tmp_wd):
    """Check that persistent files can be retrieved as artifacts.

    The path to artifact uri is retrieved through attribute ``job_directory`` of the
    archive manager.
    """
    model = create_model(
        "MockModelFields",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.cache = None
    model.execute()
    result = model.archive_manager.get_result()
    assert result["outputs"][MetaDataNames.directory_archive_job] == str(
        model.archive_manager.job_directory
    )


def test_directory_archive_job_is_known_before_publication(tmp_wd):
    """Check that the metadata of a model output already holds the artifact directory.

    The run is created before the job is executed, not when its results are
    published, so the outputs returned by ``execute`` match the archive.
    """
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.cache = None
    outputs = model.execute()

    directory = str(model.archive_manager.job_directory)
    assert directory != ""
    assert outputs[MetaDataNames.directory_archive_job][0] == directory


def test_run_is_finished_after_execution(tmp_wd):
    """Check that a run is closed once the results are published."""
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.cache = None
    model.execute()
    run = model.archive_manager._mlflow_client.get_run(
        model.archive_manager._current_run_id
    )
    assert run.info.status == "FINISHED"


def test_each_execution_creates_its_own_run(tmp_wd):
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.cache = None
    model.execute({"x1": atleast_1d(1.0), "x2": atleast_1d(2.0)})
    first_run_id = model.archive_manager._current_run_id
    model.execute({"x1": atleast_1d(3.0), "x2": atleast_1d(4.0)})
    assert model.archive_manager._current_run_id != first_run_id
    assert len(model.archive_manager.get_archived_results()) == 2


def test_delete_policy_deletes_the_current_run(tmp_wd):
    """Check that a deleting persistency policy deletes the current run.

    The run of the previous execution must be kept.
    """
    kept = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    kept.cache = None
    kept.execute()
    kept_run_id = kept.archive_manager._current_run_id

    deleted = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(
            archive_manager="MlflowArchive",
            directory_archive_persistency=PersistencyPolicy.DELETE_ALWAYS,
        ),
    )
    deleted.cache = None
    deleted.execute()

    # The run of the first model is still there, and no run was left behind
    # by the second one.
    results = kept.archive_manager.get_archived_results()
    assert len(results) == 1
    assert (
        kept.archive_manager._mlflow_client.get_run(kept_run_id).info.lifecycle_stage
        == "active"
    )
    client = kept.archive_manager._mlflow_client
    experiment_id = client.get_experiment_by_name(
        kept.archive_manager.experiment_name
    ).experiment_id
    assert len(client.search_runs([experiment_id])) == 1


def test_failed_execution_marks_the_run_as_failed(tmp_wd):
    """Check that a job which raises does not leave a run in state RUNNING."""
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.cache = None

    def raise_error(*args, **kwargs):
        msg = "boom"
        raise RuntimeError(msg)

    model._chain.execute = raise_error
    with pytest.raises(RuntimeError, match="boom"):
        model.execute()

    run_id = model.archive_manager._current_run_id
    assert run_id != ""
    assert model.archive_manager._mlflow_client.get_run(run_id).info.status == "FAILED"
    # A failed run has no results: it must not be returned by the archive.
    assert len(model.archive_manager.get_archived_results()) == 0


def test_archives_with_different_uris_do_not_interfere(tmp_wd):
    """Check that an archive is not disturbed by another one created after it.

    Each archive must only rely on its own tracking uri, and not on a state of
    MLflow shared by the whole process (the last created archive would win).
    """
    models = []
    for root in ["archive_A", "archive_B"]:
        model = create_model(
            "MockModelFields",
            "LC1",
            model_options=IntegratedModelSettings(
                archive_manager="MlflowArchive", directory_archive_root=root
            ),
        )
        model.cache = None
        models.append(model)
    model_a, model_b = models
    assert model_a.archive_manager.uri != model_b.archive_manager.uri

    # Persistent files are copied as artifacts, and results are read back, in the
    # store of the archive of the model, whichever archive was created last.
    model_a.execute()
    model_b.execute()
    for model in models:
        assert len(model.archive_manager.get_archived_results()) == 1
        artifacts = list(model.archive_manager.job_directory.iterdir())
        assert len(artifacts) > 0
    assert "archive_A" in str(model_a.archive_manager.job_directory)
    assert "archive_B" in str(model_b.archive_manager.job_directory)


def test_archive_does_not_change_the_global_tracking_uri(tmp_wd):
    """Check that creating an archive leaves the tracking uri of the process alone.

    A script which uses the MLflow API directly must set the uri itself, with
    ``mlflow.set_tracking_uri(archive_manager.uri)``.
    """
    uri_before = mlflow.get_tracking_uri()
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.cache = None
    model.execute()
    assert mlflow.get_tracking_uri() == uri_before

    mlflow.set_tracking_uri(model.archive_manager.uri)
    experiment = mlflow.get_experiment_by_name(model.archive_manager.experiment_name)
    assert len(mlflow.search_runs(experiment_ids=[experiment.experiment_id])) == 1


def test_run_ids_are_stored_in_the_run(tmp_wd):
    """Check that the identifiers of the simulation are kept in the MLflow run.

    The ``run_id`` of VIMSEO is not the one of MLflow.
    """
    model = create_model(
        "MockModelPersistent",
        "LC1",
        model_options=IntegratedModelSettings(archive_manager="MlflowArchive"),
    )
    model.cache = None
    outputs = model.execute()

    run = model.archive_manager._mlflow_client.get_run(
        model.archive_manager._current_run_id
    )
    assert run.data.tags[MetaDataNames.run_id] == outputs[MetaDataNames.run_id][0]
    assert run.data.tags[MetaDataNames.run_id] != run.info.run_id
    assert run.data.tags[MetaDataNames.tool_run_id] == ""

    result = model.archive_manager.get_result()
    assert (
        result["outputs"][MetaDataNames.run_id][0] == outputs[MetaDataNames.run_id][0]
    )
