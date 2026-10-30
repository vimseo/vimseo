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

"""Tests of the archive of the results of the analysis nodes."""

from __future__ import annotations

import json
import logging
from functools import partial
from pathlib import Path

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from openturns import ComposedDistribution
from openturns import Uniform

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_result import assert_results_equal
from vimseo.analysis_nodes.bayes.bayes_analysis import BayesAnalysisNode
from vimseo.analysis_nodes.calibration.direct_measure_calibration_step import (
    DirectMeasures,
)
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueAnalysisNode,
)
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueInputs,
)
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueSettings,
)
from vimseo.analysis_nodes.doe.custom_doe import CustomDOEAnalysisNode
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.analysis_nodes.doe.doe_result import DOEResult
from vimseo.analysis_nodes.io.reader_file_dataframe import ReaderFileDataFrame
from vimseo.analysis_nodes.io.reader_file_dataset import ReaderFileGemseoDataset
from vimseo.analysis_nodes.io.reader_file_result import ResultFileReaderAnalysisNode
from vimseo.analysis_nodes.io.reader_file_tecplot import ReaderFileTecplot
from vimseo.analysis_nodes.io.reader_material import MaterialReader
from vimseo.analysis_nodes.io.reader_parameter_space import ParameterSpaceReader
from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNode
from vimseo.analysis_nodes.mock.mock_analysis_node import MyBaseCompositeAnalysisNode
from vimseo.analysis_nodes.verification.solution_verification import (
    DiscretizationSolutionVerification,
)
from vimseo.analysis_nodes.verification.solution_verification_case import (
    SolutionVerificationCase,
)
from vimseo.analysis_nodes.verification.verification_vs_data import (
    CodeVerificationAgainstData,
)
from vimseo.analysis_nodes.verification.verification_vs_model import (
    CodeVerificationAgainstModel,
)
from vimseo.analysis_nodes.verification.verification_vs_model_from_parameter_space import (
    CodeVerificationAgainstModelFromParameterSpace,
)
from vimseo.api import create_model
from vimseo.config.global_configuration import _configuration as config
from vimseo.core.model_metadata import MetaDataNames
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.storage_management.analysis_node_archive import open_analysis_node_archive
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    NullAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    _to_json_value,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    summary_to_json,
)
from vimseo.storage_management.analysis_node_archive.directory_analysis_node_archive import (
    DirectoryAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.uri import (
    get_default_archive_manager,
)
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import generate_dataset

N_SAMPLES = 3


class FailingAnalysisNode(MyAnalysisNode):
    """An analysis node which raises."""

    @BaseAnalysisNode._validate
    def execute(self, inputs=None, settings=None, **options):
        msg = "boom"
        raise RuntimeError(msg)


@pytest.fixture
def directory_archive_root(tmp_wd):
    return tmp_wd / "analysis_node_archive"


@pytest.fixture(params=["DirectoryArchive", "MlflowArchive"])
def manager(request) -> str:
    """The name of an archive manager of the analysis node results."""
    if request.param == "MlflowArchive":
        pytest.importorskip("mlflow")
    return request.param


@pytest.fixture
def archive(directory_archive_root, manager):
    """An archive of the analysis node results, for each backend."""
    return open_analysis_node_archive(manager, directory_archive_root)


@pytest.fixture
def parameter_space():
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, minimum=-1.0, maximum=1.0
    )
    return parameter_space


def execute_doe(
    directory_archive_root, parameter_space, manager="DirectoryArchive"
) -> tuple[DOEAnalysisNode, MockModel]:
    model = MockModel("LC1")
    model.cache = None
    analysis_node = DOEAnalysisNode(
        archive_manager=manager, directory_archive_root=directory_archive_root
    )
    analysis_node.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )
    return analysis_node, model


def test_result_is_archived_after_execution(directory_archive_root, parameter_space):
    analysis_node, _ = execute_doe(directory_archive_root, parameter_space)
    run_id = analysis_node.result.metadata.analysis_node_run_id

    # The files are named after the analysis node, as the results saved by the analysis node.
    directory = (
        directory_archive_root
        / "default_study"
        / "analysis_nodes"
        / "DOEAnalysisNode"
        / run_id
    )
    assert {path.name for path in directory.iterdir()} == {
        "DOEAnalysisNode_result.hdf5",
        "DOEAnalysisNode_result_metadata.json",
    }
    summary = json.loads(
        (directory / "DOEAnalysisNode_result_metadata.json").read_text()
    )
    assert summary["status"] == "FINISHED"
    assert summary["analysis_node_run_id"] == run_id
    assert summary["analysis_node_name"] == "DOEAnalysisNode"
    assert summary["result_class"] == "DOEResult"
    assert summary["simulation_run_ids"] == list(
        analysis_node.result.metadata.simulation_run_ids
    )
    assert summary["settings"]["algo"] == "OT_OPT_LHS"


def test_archived_result_is_exactly_the_result(
    directory_archive_root, archive, manager, parameter_space
):
    analysis_node, _ = execute_doe(directory_archive_root, parameter_space, manager)

    loaded = archive.get_analysis_node_result(
        analysis_node.result.metadata.analysis_node_run_id
    )

    assert isinstance(loaded, DOEResult)
    assert_results_equal(analysis_node.result, loaded)


def test_get_analysis_node_result_of_an_unknown_run(archive):
    with pytest.raises(KeyError, match="No archived analysis node run"):
        archive.get_analysis_node_result("unknown_run_id")


def test_search_analysis_node_runs(
    directory_archive_root, archive, manager, parameter_space
):
    first, _ = execute_doe(directory_archive_root, parameter_space, manager)
    second, _ = execute_doe(directory_archive_root, parameter_space, manager)

    runs = archive.search_analysis_node_runs()
    assert {run["analysis_node_run_id"] for run in runs} == {
        first.result.metadata.analysis_node_run_id,
        second.result.metadata.analysis_node_run_id,
    }
    assert (
        archive.search_analysis_node_runs(analysis_node_name="DOEAnalysisNode") == runs
    )
    assert (
        archive.search_analysis_node_runs(analysis_node_name="AnotherAnalysisNode")
        == []
    )
    assert archive.search_analysis_node_runs(status="FAILED") == []


def test_find_the_analysis_node_runs_of_a_simulation(
    directory_archive_root, archive, manager
):
    """Check the way from a simulation to the analysis node runs: a simulation retrieved from
    the cache is found by every analysis node run which used it."""
    model = MockModel("LC1")
    input_dataset = generate_dataset(
        {IODataset.INPUT_GROUP: [Variable("x1", 0.5, is_constant_value=True)]}, 2
    )
    analysis_nodes = [
        CustomDOEAnalysisNode(
            archive_manager=manager, directory_archive_root=directory_archive_root
        )
        for _ in range(2)
    ]
    for analysis_node in analysis_nodes:
        analysis_node.execute(
            model=model, input_dataset=input_dataset, output_names=["y1"]
        )
    run_ids = {
        analysis_node.result.metadata.analysis_node_run_id
        for analysis_node in analysis_nodes
    }
    (simulation_id,) = analysis_nodes[0].result.metadata.simulation_run_ids

    assert set(archive.find_analysis_node_runs_of_simulation(simulation_id)) == run_ids
    assert archive.find_analysis_node_runs_of_simulation("unknown_simulation") == []


def test_find_the_simulations_of_an_analysis_node_run(
    directory_archive_root, archive, manager, parameter_space
):
    """Check the way from an analysis node run to its simulations, the other way of the link:
    the summary and the result give the same ones, which are the simulations of
    the model archive."""
    analysis_node, model = execute_doe(directory_archive_root, parameter_space, manager)
    run_id = analysis_node.result.metadata.analysis_node_run_id

    (summary,) = archive.search_analysis_node_runs()
    from_result = archive.get_analysis_node_result(run_id).metadata.simulation_run_ids
    archived = {
        str(r["outputs"][MetaDataNames.run_id][0])
        for r in model.archive_manager.get_archived_results()
    }

    assert len(from_result) == N_SAMPLES
    assert set(summary["simulation_run_ids"]) == set(from_result) == archived


def test_failed_analysis_node_run_is_archived_as_failed(
    directory_archive_root, archive, manager
):
    analysis_node = FailingAnalysisNode(
        archive_manager=manager, directory_archive_root=directory_archive_root
    )
    with pytest.raises(RuntimeError, match="boom"):
        analysis_node.execute()

    (summary,) = archive.search_analysis_node_runs()
    assert summary["status"] == "FAILED"
    assert summary["error"] == "RuntimeError: boom"
    with pytest.raises(KeyError, match="has no"):
        archive.get_analysis_node_result(summary["analysis_node_run_id"])
    assert archive.search_analysis_node_runs(status="FAILED") == [summary]


def test_sub_analysis_nodes_are_archived_with_their_parent(
    directory_archive_root, archive, manager
):
    sub_analysis_node = MyAnalysisNode(
        archive_manager=manager, directory_archive_root=directory_archive_root
    )
    composite = MyBaseCompositeAnalysisNode(
        sub_analysis_nodes=[sub_analysis_node],
        archive_manager=manager,
        directory_archive_root=directory_archive_root,
    )
    composite.execute()

    composite_id = composite.result.metadata.analysis_node_run_id
    sub_id = sub_analysis_node.result.metadata.analysis_node_run_id
    summaries = {
        run["analysis_node_run_id"]: run for run in archive.search_analysis_node_runs()
    }

    assert set(summaries) == {composite_id, sub_id}
    assert summaries[sub_id]["parent_analysis_node_run_id"] == composite_id
    assert summaries[composite_id]["child_analysis_node_run_ids"] == [sub_id]


def test_sub_analysis_nodes_inherit_the_archive_of_their_parent(
    directory_archive_root, archive, manager
):
    """The sub-analysis nodes created without archive settings, as the composite analysis nodes do,
    archive their results with their parent, at any depth of nesting."""
    inner = MyBaseCompositeAnalysisNode(
        name="inner", sub_analysis_nodes=[MyAnalysisNode()]
    )
    outer = MyBaseCompositeAnalysisNode(
        sub_analysis_nodes=[inner],
        archive_manager=manager,
        directory_archive_root=directory_archive_root,
    )
    outer.execute()

    names = {run["analysis_node_name"] for run in archive.search_analysis_node_runs()}
    assert names == {"MyBaseCompositeAnalysisNode", "inner", "MyAnalysisNode"}


def test_explicit_archive_settings_of_a_sub_analysis_node_are_kept(
    directory_archive_root, archive, manager
):
    sub_analysis_node = MyAnalysisNode(archive_manager="none")
    composite = MyBaseCompositeAnalysisNode(
        sub_analysis_nodes=[sub_analysis_node],
        archive_manager=manager,
        directory_archive_root=directory_archive_root,
    )
    composite.execute()

    assert isinstance(
        sub_analysis_node._analysis_node_archive_manager, NullAnalysisNodeArchive
    )
    (run,) = archive.search_analysis_node_runs()
    assert run["analysis_node_name"] == "MyBaseCompositeAnalysisNode"


@pytest.mark.parametrize(
    "analysis_node_class",
    [
        DiscretizationSolutionVerification,
        CodeVerificationAgainstData,
        CodeVerificationAgainstModel,
        CodeVerificationAgainstModelFromParameterSpace,
        SolutionVerificationCase,
        DirectMeasures,
        ReaderFileDataFrame,
        ReaderFileGemseoDataset,
        ReaderFileTecplot,
        MaterialReader,
        ParameterSpaceReader,
        partial(ResultFileReaderAnalysisNode, "SpaceAnalysisNode"),
    ],
    ids=lambda analysis_node_class: getattr(
        analysis_node_class, "__name__", "ResultFileReaderAnalysisNode"
    ),
)
def test_analysis_nodes_with_their_own_constructor_accept_the_archive_settings(
    directory_archive_root, analysis_node_class
):
    """The analysis nodes defining their own constructor pass the archive settings to their
    base class, and to their sub-analysis nodes."""
    analysis_node = analysis_node_class(
        archive_manager="DirectoryArchive",
        directory_archive_root=directory_archive_root,
    )

    for archived_analysis_node in [
        analysis_node,
        *getattr(analysis_node, "_sub_analysis_nodes", {}).values(),
    ]:
        assert isinstance(
            archived_analysis_node._analysis_node_archive_manager,
            DirectoryAnalysisNodeArchive,
        )
        assert (
            archived_analysis_node._analysis_node_archive_manager.root_directory
            == str(directory_archive_root.absolute())
        )


def test_an_error_of_the_archive_does_not_lose_the_result(
    directory_archive_root, parameter_space, monkeypatch, caplog
):
    def fail(self, result):
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(
        DirectoryAnalysisNodeArchive, "publish_analysis_node_result", fail
    )
    with caplog.at_level(logging.ERROR):
        analysis_node, _ = execute_doe(directory_archive_root, parameter_space)

    assert analysis_node.result.dataset is not None
    assert "could not be archived" in caplog.text
    assert "disk full" in caplog.text


def test_analysis_node_archive_is_disabled_in_the_tests(tmp_wd):
    """Check the fixture of the tests, which relies on the configuration."""
    assert isinstance(
        MyAnalysisNode()._analysis_node_archive_manager, NullAnalysisNodeArchive
    )
    assert not (tmp_wd / "default_archive").exists()


def test_archive_manager_comes_from_the_configuration(tmp_wd, monkeypatch):
    monkeypatch.setattr(config, "analysis_node_archive_manager", "DirectoryArchive")
    assert isinstance(
        MyAnalysisNode()._analysis_node_archive_manager, DirectoryAnalysisNodeArchive
    )

    # Without ``analysis_node_archive_manager``, it is the one of the simulations.
    monkeypatch.setattr(config, "analysis_node_archive_manager", None)
    monkeypatch.setattr(config, "run_archive_manager", "DirectoryArchive")
    assert isinstance(
        MyAnalysisNode()._analysis_node_archive_manager, DirectoryAnalysisNodeArchive
    )

    # The setting of the analysis node takes precedence over the configuration.
    assert isinstance(
        MyAnalysisNode(archive_manager="none")._analysis_node_archive_manager,
        NullAnalysisNodeArchive,
    )


def test_default_archive_root(tmp_wd):
    archive = MyAnalysisNode(
        archive_manager="DirectoryArchive"
    )._analysis_node_archive_manager
    assert archive.root_directory == str((tmp_wd / "default_archive").absolute())

    archive = MyAnalysisNode(
        archive_manager="DirectoryArchive", directory_archive_root=tmp_wd / "other"
    )._analysis_node_archive_manager
    assert archive.root_directory == str((tmp_wd / "other").absolute())


def test_unknown_archive_manager():
    with pytest.raises(ValueError, match="Unknown archive manager"):
        open_analysis_node_archive("Unknown", "root")


def test_mlflow_runs_of_sub_analysis_nodes_are_nested(directory_archive_root):
    """In MLflow, the run of a sub-analysis node is nested in the run of its parent analysis node, in a
    single experiment."""
    pytest.importorskip("mlflow")
    sub_analysis_node = MyAnalysisNode(
        archive_manager="MlflowArchive", directory_archive_root=directory_archive_root
    )
    composite = MyBaseCompositeAnalysisNode(
        sub_analysis_nodes=[sub_analysis_node],
        archive_manager="MlflowArchive",
        directory_archive_root=directory_archive_root,
    )
    composite.execute()

    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    summaries = {
        run["analysis_node_run_id"]: run for run in archive.search_analysis_node_runs()
    }
    parent = summaries[composite.result.metadata.analysis_node_run_id]
    child = summaries[sub_analysis_node.result.metadata.analysis_node_run_id]
    child_run = archive._client.get_run(child["mlflow_run_id"])
    assert child_run.data.tags["mlflow.parentRunId"] == parent["mlflow_run_id"]
    assert child_run.info.experiment_id == archive.experiment_id
    # The result is also reachable from the id of its MLflow run.
    assert_results_equal(
        sub_analysis_node.result,
        archive.get_analysis_node_result_of_mlflow_run(child["mlflow_run_id"]),
    )


def test_mlflow_result_published_again(directory_archive_root, parameter_space):
    """A result completed after the execution of the analysis node, then published again,
    replaces the archived one."""
    pytest.importorskip("mlflow")
    analysis_node, _ = execute_doe(
        directory_archive_root, parameter_space, "MlflowArchive"
    )
    analysis_node.result.metadata.misc["completed"] = True
    analysis_node._republish_result()

    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    loaded = archive.get_analysis_node_result(
        analysis_node.result.metadata.analysis_node_run_id
    )
    assert loaded.metadata.misc["completed"]
    (summary,) = archive.search_analysis_node_runs()
    assert summary["status"] == "FINISHED"


def test_openturns_settings_are_described_in_clear(
    directory_archive_root, archive, manager
):
    """The prior of a Bayesian analysis, an OpenTURNS distribution, is described in
    clear in the summary of the analysis node run, not by the address of a Python object."""
    analysis_node = BayesAnalysisNode(
        archive_manager=manager, directory_archive_root=directory_archive_root
    )
    analysis_node.execute(
        likelihood_dist="Normal",
        prior_dist=ComposedDistribution([Uniform(0, 5)] * 2),
        data=array([1.0, 2.0, 3.0]),
        n_mcmc=2,
    )

    (summary,) = archive.search_analysis_node_runs()
    prior = summary["settings"]["prior_dist"]
    assert "Swig" not in str(prior)
    if manager == "MlflowArchive":
        # An MLflow parameter, in short form.
        assert prior.startswith("ComposedDistribution(Uniform(a = 0, b = 5)")
    else:
        assert prior["kind"] == "joint"
        assert prior["marginals"][0]["settings"]["name"] == "Uniform"


def _create_mlflow_model(directory_archive_root):
    """A model whose simulations are in the MLflow database of the analysis node runs."""
    return create_model(
        "MockModel",
        "LC1",
        archive_manager="MlflowArchive",
        directory_archive_root=directory_archive_root,
    )


def _get_simulation_runs(archive, model):
    """Return the MLflow runs of the simulations of a model."""
    experiment = archive._client.get_experiment_by_name(
        model.archive_manager.study_name
    )
    return archive._client.search_runs(
        [experiment.experiment_id],
        filter_string=(
            "tags.`vimseo.kind` = 'simulation' "
            f"and tags.`vimseo.model` = '{model.name}'"
        ),
    )


def test_mlflow_analysis_node_runs_are_linked_to_their_simulations(
    directory_archive_root,
):
    """The analysis node run links to its simulations, and the simulations to the analysis node runs
    which used them, including from the cache of the model."""
    pytest.importorskip("mlflow")
    model = _create_mlflow_model(directory_archive_root)
    input_dataset = generate_dataset(
        {IODataset.INPUT_GROUP: [Variable("x1", 0.5, is_constant_value=True)]}, 2
    )
    analysis_nodes = [
        CustomDOEAnalysisNode(
            archive_manager="MlflowArchive",
            directory_archive_root=directory_archive_root,
        )
        for _ in range(2)
    ]
    for analysis_node in analysis_nodes:
        analysis_node.execute(
            model=model, input_dataset=input_dataset, output_names=["y1"]
        )
    first_id, second_id = (
        analysis_node.result.metadata.analysis_node_run_id
        for analysis_node in analysis_nodes
    )

    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    (simulation,) = _get_simulation_runs(archive, model)
    # The second analysis node run retrieved the simulation from the cache: it is linked too.
    assert json.loads(simulation.data.tags["vimseo.analysis_node_run_ids"]) == [
        first_id,
        second_id,
    ]
    experiment_id = simulation.info.experiment_id
    found = archive._client.search_runs(
        [experiment_id],
        filter_string=f"tags.`vimseo.analysis_node_run_ids` LIKE '%{second_id}%'",
    )
    assert [run.info.run_id for run in found] == [simulation.info.run_id]

    summaries = {
        run["analysis_node_run_id"]: run for run in archive.search_analysis_node_runs()
    }
    description = archive._client.get_run(
        summaries[second_id]["mlflow_run_id"]
    ).data.tags["mlflow.note.content"]
    assert f"#/experiments/{experiment_id}/runs/{simulation.info.run_id}" in description
    assert "1 simulations" in description


def test_mlflow_sub_analysis_node_runs_are_linked(directory_archive_root):
    """The description of an analysis node run links to its parent and to its sub-analysis nodes."""
    pytest.importorskip("mlflow")
    sub_analysis_node = MyAnalysisNode(
        archive_manager="MlflowArchive", directory_archive_root=directory_archive_root
    )
    composite = MyBaseCompositeAnalysisNode(
        sub_analysis_nodes=[sub_analysis_node],
        archive_manager="MlflowArchive",
        directory_archive_root=directory_archive_root,
    )
    composite.execute()

    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    summaries = {
        run["analysis_node_run_id"]: run for run in archive.search_analysis_node_runs()
    }
    parent = summaries[composite.result.metadata.analysis_node_run_id]["mlflow_run_id"]
    child = summaries[sub_analysis_node.result.metadata.analysis_node_run_id][
        "mlflow_run_id"
    ]

    def description(run_id):
        return archive._client.get_run(run_id).data.tags["mlflow.note.content"]

    assert f"/runs/{child})" in description(parent)
    assert f"/runs/{parent})" in description(child)


def test_mlflow_analysis_node_run_without_simulation(directory_archive_root):
    """An analysis node run without model nor simulation has a description without link."""
    pytest.importorskip("mlflow")
    analysis_node = BayesAnalysisNode(
        archive_manager="MlflowArchive", directory_archive_root=directory_archive_root
    )
    analysis_node.execute(
        likelihood_dist="Normal",
        prior_dist=ComposedDistribution([Uniform(0, 5)] * 2),
        data=array([1.0, 2.0, 3.0]),
        n_mcmc=2,
    )
    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    (summary,) = archive.search_analysis_node_runs()
    description = archive._client.get_run(summary["mlflow_run_id"]).data.tags[
        "mlflow.note.content"
    ]
    assert "simulations" not in description


def test_mlflow_analysis_node_run_without_model_linked_to_simulations(
    directory_archive_root, parameter_space
):
    """A design value has no model in its result, but the simulations of its DOE are
    linked to it: they are searched in all the experiments."""
    pytest.importorskip("mlflow")
    model = _create_mlflow_model(directory_archive_root)
    analysis_node = DesignValueAnalysisNode(
        archive_manager="MlflowArchive", directory_archive_root=directory_archive_root
    )
    analysis_node.execute(
        inputs=DesignValueInputs(model=model, parameter_space=parameter_space),
        settings=DesignValueSettings(output_names=["y1"], n_samples=N_SAMPLES),
    )
    assert analysis_node.result.metadata.model is None

    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    (summary,) = archive.search_analysis_node_runs(
        analysis_node_name="DesignValueAnalysisNode"
    )
    description = archive._client.get_run(summary["mlflow_run_id"]).data.tags[
        "mlflow.note.content"
    ]
    simulations = _get_simulation_runs(archive, model)
    assert len(simulations) == N_SAMPLES
    for simulation in simulations:
        assert f"/runs/{simulation.info.run_id})" in description
        assert summary["analysis_node_run_id"] in json.loads(
            simulation.data.tags["vimseo.analysis_node_run_ids"]
        )


def test_key_values_are_archived(
    directory_archive_root, archive, manager, parameter_space
):
    """The numbers summarizing a result are in the summary of its analysis node run, and are
    MLflow metrics."""
    execute_doe(directory_archive_root, parameter_space, manager)
    (summary,) = archive.search_analysis_node_runs()
    assert summary["key_values"] == {"n_samples": N_SAMPLES}
    if manager == "MlflowArchive":
        run = archive._client.get_run(summary["mlflow_run_id"])
        assert run.data.metrics == {"n_samples": N_SAMPLES}


def test_an_analysis_node_and_a_model_share_the_archive_settings(
    tmp_wd, parameter_space
):
    """An analysis node and a model built with the same archive settings use the same root."""
    from vimseo.storage_management.archive_settings import ArchiveLocationSettings

    settings = ArchiveLocationSettings(
        archive_manager="DirectoryArchive", directory_archive_root=tmp_wd / "shared"
    ).model_dump()
    model = MockModel("LC1", **settings)
    analysis_node = DOEAnalysisNode(**settings)
    assert Path(model.archive_manager.root_directory) == Path(
        analysis_node._analysis_node_archive_manager.root_directory
    )


def test_archive_root_is_no_longer_accepted():
    """The former name of directory_archive_root raises an error."""
    with pytest.raises(TypeError, match="archive_root"):
        MyAnalysisNode(archive_root="root")


def test_to_json_value_never_fails(monkeypatch):
    """A value that cannot be described in clear is described by its short form."""
    from vimseo.utilities import ot_distribution_io

    value = object()
    assert _to_json_value(value) == repr(value)

    def fail(distribution):
        msg = "not describable"
        raise ValueError(msg)

    monkeypatch.setattr(ot_distribution_io, "ot_distribution_to_dict", fail)
    distribution = Uniform(0, 1)
    assert _to_json_value(distribution) == str(distribution)


def test_summary_to_json_skips_the_keys_which_are_not_strings():
    summary = json.loads(summary_to_json({"settings": {(1, 2): 3, "a": 4}}))
    assert summary == {"settings": {"a": 4}}


def test_study_name_of_an_archive(archive):
    archive.set_study_name("other_study")
    assert archive.study_name == "other_study"


def test_null_archive():
    archive = NullAnalysisNodeArchive()
    with pytest.raises(KeyError, match="disabled"):
        archive.get_analysis_node_result("run_id")
    assert archive.search_analysis_node_runs() == []
    assert archive.find_analysis_node_runs_of_simulation("run_id") == []


def test_default_archive_manager_when_the_archive_is_disabled(monkeypatch):
    """Disabling the archive of the new analysis node runs does not prevent from reading
    the former ones, from the archive of the simulations."""
    monkeypatch.setattr(config, "analysis_node_archive_manager", "none")
    monkeypatch.setattr(config, "run_archive_manager", "DirectoryArchive")
    assert get_default_archive_manager() == "DirectoryArchive"

    monkeypatch.setattr(config, "analysis_node_archive_manager", "MlflowArchive")
    assert get_default_archive_manager() == "MlflowArchive"


def test_mlflow_result_found_from_its_analysis_node_name(
    directory_archive_root, parameter_space
):
    pytest.importorskip("mlflow")
    analysis_node, _ = execute_doe(
        directory_archive_root, parameter_space, "MlflowArchive"
    )
    run_id = analysis_node.result.metadata.analysis_node_run_id
    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    assert_results_equal(
        analysis_node.result,
        archive.get_analysis_node_result(run_id, analysis_node_name="DOEAnalysisNode"),
    )
    with pytest.raises(KeyError):
        archive.get_analysis_node_result(run_id, analysis_node_name="MyAnalysisNode")


def test_mlflow_link_error_does_not_lose_the_result(
    directory_archive_root, parameter_space, monkeypatch, caplog
):
    """The links to the simulations are a convenience: failing to create them is logged."""
    pytest.importorskip("mlflow")
    from vimseo.storage_management.analysis_node_archive.mlflow_analysis_node_archive import (
        MlflowAnalysisNodeArchive,
    )

    def fail(self, result):
        msg = "no link"
        raise RuntimeError(msg)

    monkeypatch.setattr(MlflowAnalysisNodeArchive, "_link_simulations", fail)
    with caplog.at_level(logging.ERROR):
        analysis_node, _ = execute_doe(
            directory_archive_root, parameter_space, "MlflowArchive"
        )

    assert "could not be linked to its simulations" in caplog.text
    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    assert_results_equal(
        analysis_node.result,
        archive.get_analysis_node_result(
            analysis_node.result.metadata.analysis_node_run_id
        ),
    )


def _execute_custom_does(directory_archive_root, n_does):
    """Execute DOEs archived in MLflow, sharing a single simulation."""
    model = _create_mlflow_model(directory_archive_root)
    input_dataset = generate_dataset(
        {IODataset.INPUT_GROUP: [Variable("x1", 0.5, is_constant_value=True)]}, 2
    )
    analysis_nodes = []
    for _ in range(n_does):
        analysis_node = CustomDOEAnalysisNode(
            archive_manager="MlflowArchive",
            directory_archive_root=directory_archive_root,
        )
        analysis_node.execute(
            model=model, input_dataset=input_dataset, output_names=["y1"]
        )
        analysis_nodes.append(analysis_node)
    return analysis_nodes, model


def test_mlflow_links_of_a_simulation_are_truncated(
    directory_archive_root, monkeypatch
):
    """The tag of a simulation keeps the most recent analysis node runs which fit in it,
    and a result published again is not linked twice."""
    pytest.importorskip("mlflow")
    from vimseo.storage_management.analysis_node_archive import (
        mlflow_analysis_node_archive,
    )

    # Room for a single identifier.
    monkeypatch.setattr(mlflow_analysis_node_archive, "_MAX_TAG_LENGTH", 40)
    analysis_nodes, model = _execute_custom_does(directory_archive_root, 2)
    second_id = analysis_nodes[1].result.metadata.analysis_node_run_id

    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    (simulation,) = _get_simulation_runs(archive, model)
    tags = simulation.data.tags
    assert json.loads(tags["vimseo.analysis_node_run_ids"]) == [second_id]
    assert tags["vimseo.analysis_node_run_ids_truncated"] == "true"

    analysis_nodes[1]._republish_result()
    (simulation,) = _get_simulation_runs(archive, model)
    assert json.loads(simulation.data.tags["vimseo.analysis_node_run_ids"]) == [
        second_id
    ]


def test_mlflow_long_links_are_in_the_summary_artifact(
    directory_archive_root, monkeypatch
):
    """The simulations of an analysis node run too long for a tag are read from the
    summary artifact."""
    pytest.importorskip("mlflow")
    from vimseo.storage_management.analysis_node_archive import (
        mlflow_analysis_node_archive,
    )

    monkeypatch.setattr(mlflow_analysis_node_archive, "_MAX_TAG_LENGTH", 5)
    (_analysis_node,), model = _execute_custom_does(directory_archive_root, 1)

    archive = open_analysis_node_archive("MlflowArchive", directory_archive_root)
    (summary,) = archive.search_analysis_node_runs()
    run = archive._client.get_run(summary["mlflow_run_id"])
    assert run.data.tags["vimseo.simulation_run_ids"] == "in_artifact"
    (simulation,) = _get_simulation_runs(archive, model)
    assert summary["simulation_run_ids"] == [simulation.data.tags["vimseo.run_id"]]
