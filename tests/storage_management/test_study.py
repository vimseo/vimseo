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

"""Tests of the studies, the identifiers and the statuses of the runs (SPEC-011)."""

from __future__ import annotations

import json
import logging
import re

import pytest
from numpy import atleast_1d

from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNode
from vimseo.analysis_nodes.mock.mock_analysis_node import MyBaseCompositeAnalysisNode
from vimseo.config.configuration_settings import DEFAULT_STUDY_NAME
from vimseo.config.configuration_settings import VimseoSettings
from vimseo.config.global_configuration import _configuration as config
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.run_context import new_run_id
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.storage_management.analysis_node_archive import open_analysis_node_archive

pytestmark = pytest.mark.fast

RUN_ID = re.compile(r"^\d{8}T\d{6}_[0-9a-f]{8}$")


def _create_model(root, study_name="", archive_manager="DirectoryArchive"):
    model = MockModel(
        "LC1",
        archive_manager=archive_manager,
        directory_archive_root=root,
        **({"study_name": study_name} if study_name else {}),
    )
    model.cache = None
    return model


def test_default_study(monkeypatch):
    """The default study is default_study, and VIMSEO_STUDY_NAME changes it."""
    assert VimseoSettings().study_name == DEFAULT_STUDY_NAME == "default_study"
    monkeypatch.setenv("VIMSEO_STUDY_NAME", "layup_A")
    assert VimseoSettings().study_name == "layup_A"


def test_identifiers_are_sorted_by_date():
    """An identifier is the UTC date followed by a part of a UUID."""
    first = new_run_id()
    second = new_run_id()
    assert RUN_ID.match(first)
    assert first != second
    assert first[:15] <= second[:15]


def test_job_directory_is_named_by_the_run_id(tmp_wd):
    """A simulation is archived in {root}/{study}/{model}/{load_case}/{run_id}."""
    model = _create_model(tmp_wd / "archive", "layup_A")
    output_data = model.execute({"x1": atleast_1d(1.0)})
    run_id = output_data[MetaDataNames.run_id][0]
    directory = tmp_wd / "archive" / "layup_A" / "MockModel" / "LC1" / run_id
    results = json.loads((directory / "results.json").read_text())
    assert results["metadata"][MetaDataNames.status] == "FINISHED"
    assert results["metadata"][MetaDataNames.run_id] == run_id


def test_a_failed_run_is_archived_as_failed(tmp_wd, monkeypatch):
    """The inputs are written at the start; a run which raises ends FAILED."""
    model = _create_model(tmp_wd / "archive")

    def boom(*args, **kwargs):
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(model, "archive_outputs", boom)
    with pytest.raises(RuntimeError, match="boom"):
        model.execute({"x1": atleast_1d(0.5)})

    (path,) = (tmp_wd / "archive" / DEFAULT_STUDY_NAME).glob("*/*/*/results.json")
    results = json.loads(path.read_text())
    assert results["inputs"]["x1"] == pytest.approx(0.5)
    assert results["metadata"][MetaDataNames.status] == "FAILED"
    assert results["metadata"][MetaDataNames.run_id] == path.parent.name
    # A failed run is not used to build a cache.
    assert model.archive_manager.get_archived_results() == []


def test_a_running_run_is_visible(tmp_wd, monkeypatch):
    """During a run, the archive holds its inputs with the status RUNNING."""
    model = _create_model(tmp_wd / "archive")
    statuses = []
    archive_outputs = model.archive_outputs

    def check_then_archive(output_data):
        path = model.archive_manager.job_directory / "results.json"
        statuses.append(json.loads(path.read_text())["metadata"]["status"])
        return archive_outputs(output_data)

    monkeypatch.setattr(model, "archive_outputs", check_then_archive)
    model.execute({"x1": atleast_1d(0.2)})
    assert statuses == ["RUNNING"]


def test_a_cached_execution_archives_nothing(tmp_wd):
    """An execution served by the cache archives no new simulation."""
    model = MockModel(
        "LC1", archive_manager="DirectoryArchive", directory_archive_root="archive"
    )
    model.execute({"x1": atleast_1d(1.0)})
    model.execute({"x1": atleast_1d(1.0)})
    assert len(list((tmp_wd / "archive").glob("*/*/*/*/results.json"))) == 1


def test_sub_analysis_nodes_inherit_the_study(tmp_wd):
    """A sub-analysis node without study uses the one of its parent; an explicit one wins."""
    inherited = MyAnalysisNode(name="inherited", archive_manager="DirectoryArchive")
    explicit = MyAnalysisNode(
        name="explicit", archive_manager="DirectoryArchive", study_name="other"
    )
    MyBaseCompositeAnalysisNode(
        sub_analysis_nodes=[inherited, explicit],
        archive_manager="DirectoryArchive",
        directory_archive_root=tmp_wd / "archive",
        study_name="layup_A",
    )
    assert inherited._analysis_node_archive_manager.study_name == "layup_A"
    assert explicit._analysis_node_archive_manager.study_name == "other"


def test_analysis_node_runs_are_searched_by_study(tmp_wd):
    """The analysis node runs of every study are found, and a study filters them."""
    root = tmp_wd / "archive"
    for study_name in ("layup_A", "layup_B"):
        MyAnalysisNode(
            archive_manager="DirectoryArchive",
            directory_archive_root=root,
            study_name=study_name,
        ).execute()
    archive = open_analysis_node_archive("DirectoryArchive", root)
    assert {run["study_name"] for run in archive.search_analysis_node_runs()} == {
        "layup_A",
        "layup_B",
    }
    (run,) = archive.search_analysis_node_runs(study_name="layup_B")
    assert (
        root
        / "layup_B"
        / "analysis_nodes"
        / "MyAnalysisNode"
        / run["analysis_node_run_id"]
    ).is_dir()
    # An analysis node run is found by its identifier whatever its study.
    assert archive.get_analysis_node_result(run["analysis_node_run_id"]) is not None


def test_two_models_in_one_mlflow_study(tmp_wd):
    """Two models of one MLflow study only see their own simulations."""
    pytest.importorskip("mlflow")
    from vimseo.problems.mock.mock_model_persistent.mock_model_persistent import (
        MockModelPersistent,
    )

    first = _create_model(tmp_wd / "mlflow", "study", "MlflowArchive")
    second = MockModelPersistent(
        "LC1",
        archive_manager="MlflowArchive",
        directory_archive_root=tmp_wd / "mlflow",
        study_name="study",
    )
    second.cache = None
    first.execute({"x1": atleast_1d(1.0)})
    second.execute()
    assert len(first.archive_manager.get_archived_results()) == 1
    assert len(second.archive_manager.get_archived_results()) == 1
    client = first.archive_manager._mlflow_client
    assert {experiment.name for experiment in client.search_experiments()} >= {"study"}
    (run,) = client.search_runs(
        [client.get_experiment_by_name("study").experiment_id],
        filter_string="tags.`vimseo.model` = 'MockModel'",
    )
    assert run.data.tags["vimseo.kind"] == "simulation"
    assert run.info.run_name == run.data.tags["vimseo.run_id"]


def test_team_mode_ignores_the_root(tmp_wd, monkeypatch, caplog):
    """In Team mode, an explicit directory_archive_root is ignored with a warning."""
    pytest.importorskip("mlflow")
    from vimseo.storage_management import mlflow_storage
    from vimseo.storage_management.base_storage_manager import PersistencyPolicy

    monkeypatch.setattr(config.database, "mode", "Team")
    monkeypatch.setattr(
        mlflow_storage, "get_tracking_uri", lambda root_directory="": "https://team"
    )
    monkeypatch.setattr(
        mlflow_storage.mlflow.tracking, "MlflowClient", lambda **_: None
    )
    with caplog.at_level(logging.WARNING):
        mlflow_storage.MlflowArchive(
            PersistencyPolicy.DELETE_NEVER, root_directory=tmp_wd / "ignored"
        )
    assert "is ignored" in caplog.text
