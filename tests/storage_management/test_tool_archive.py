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

"""Tests of the archive of the results of the tools."""

from __future__ import annotations

import json
import logging
from functools import partial

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from openturns import ComposedDistribution
from openturns import Uniform

from vimseo.api import create_model
from vimseo.config.global_configuration import _configuration as config
from vimseo.core.model_metadata import MetaDataNames
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.storage_management.tool_archive import open_tool_archive
from vimseo.storage_management.tool_archive.base_tool_archive import NullToolArchive
from vimseo.storage_management.tool_archive.directory_tool_archive import (
    DirectoryToolArchive,
)
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.bayes.bayes_analysis import BayesTool
from vimseo.tools.calibration.direct_measure_calibration_step import DirectMeasures
from vimseo.tools.design_value.design_value_tool import DesignValueInputs
from vimseo.tools.design_value.design_value_tool import DesignValueSettings
from vimseo.tools.design_value.design_value_tool import DesignValueTool
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.doe.doe_result import DOEResult
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrame
from vimseo.tools.io.reader_file_dataset import ReaderFileGemseoDataset
from vimseo.tools.io.reader_file_result import ResultFileReaderTool
from vimseo.tools.io.reader_file_tecplot import ReaderFileTecplot
from vimseo.tools.io.reader_material import MaterialReader
from vimseo.tools.io.reader_parameter_space import ParameterSpaceReader
from vimseo.tools.mock.mock_tool import MyBaseCompositeTool
from vimseo.tools.mock.mock_tool import MyTool
from vimseo.tools.verification.solution_verification import (
    DiscretizationSolutionVerification,
)
from vimseo.tools.verification.solution_verification_case import (
    SolutionVerificationCase,
)
from vimseo.tools.verification.verification_vs_data import CodeVerificationAgainstData
from vimseo.tools.verification.verification_vs_model import CodeVerificationAgainstModel
from vimseo.tools.verification.verification_vs_model_from_parameter_space import (
    CodeVerificationAgainstModelFromParameterSpace,
)
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import generate_dataset

N_SAMPLES = 3


class FailingTool(MyTool):
    """A tool which raises."""

    @BaseTool.validate
    def execute(self, inputs=None, settings=None, **options):
        msg = "boom"
        raise RuntimeError(msg)


@pytest.fixture
def archive_root(tmp_wd):
    return tmp_wd / "tool_archive"


@pytest.fixture(params=["DirectoryArchive", "MlflowArchive"])
def manager(request) -> str:
    """The name of an archive manager of the tool results."""
    if request.param == "MlflowArchive":
        pytest.importorskip("mlflow")
    return request.param


@pytest.fixture
def archive(archive_root, manager):
    """An archive of the tool results, for each backend."""
    return open_tool_archive(manager, archive_root)


@pytest.fixture
def parameter_space():
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, minimum=-1.0, maximum=1.0
    )
    return parameter_space


def execute_doe(
    archive_root, parameter_space, manager="DirectoryArchive"
) -> tuple[DOETool, MockModel]:
    model = MockModel("LC1")
    model.cache = None
    tool = DOETool(archive_manager=manager, archive_root=archive_root)
    tool.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )
    return tool, model


def test_result_is_archived_after_execution(archive_root, parameter_space):
    tool, _ = execute_doe(archive_root, parameter_space)
    run_id = tool.result.metadata.tool_run_id

    # The files are named after the tool, as the results saved by the tool.
    directory = archive_root / "tools" / "DOETool" / run_id
    assert {path.name for path in directory.iterdir()} == {
        "DOETool_result.hdf5",
        "DOETool_result_metadata.json",
    }
    summary = json.loads((directory / "DOETool_result_metadata.json").read_text())
    assert summary["status"] == "FINISHED"
    assert summary["tool_run_id"] == run_id
    assert summary["tool_name"] == "DOETool"
    assert summary["result_class"] == "DOEResult"
    assert summary["simulation_run_ids"] == list(
        tool.result.metadata.simulation_run_ids
    )
    assert summary["settings"]["algo"] == "OT_OPT_LHS"


def test_archived_result_is_exactly_the_result(
    archive_root, archive, manager, parameter_space
):
    tool, _ = execute_doe(archive_root, parameter_space, manager)

    loaded = archive.get_tool_result(tool.result.metadata.tool_run_id)

    assert isinstance(loaded, DOEResult)
    assert_results_equal(tool.result, loaded)


def test_get_tool_result_of_an_unknown_run(archive):
    with pytest.raises(KeyError, match="No archived tool run"):
        archive.get_tool_result("unknown_run_id")


def test_search_tool_runs(archive_root, archive, manager, parameter_space):
    first, _ = execute_doe(archive_root, parameter_space, manager)
    second, _ = execute_doe(archive_root, parameter_space, manager)

    runs = archive.search_tool_runs()
    assert {run["tool_run_id"] for run in runs} == {
        first.result.metadata.tool_run_id,
        second.result.metadata.tool_run_id,
    }
    assert archive.search_tool_runs(tool_name="DOETool") == runs
    assert archive.search_tool_runs(tool_name="AnotherTool") == []
    assert archive.search_tool_runs(status="FAILED") == []


def test_find_the_tool_runs_of_a_simulation(archive_root, archive, manager):
    """Check the way from a simulation to the tool runs: a simulation retrieved from
    the cache is found by every tool run which used it."""
    model = MockModel("LC1")
    input_dataset = generate_dataset(
        {IODataset.INPUT_GROUP: [Variable("x1", 0.5, is_constant_value=True)]}, 2
    )
    tools = [
        CustomDOETool(archive_manager=manager, archive_root=archive_root)
        for _ in range(2)
    ]
    for tool in tools:
        tool.execute(model=model, input_dataset=input_dataset, output_names=["y1"])
    run_ids = {tool.result.metadata.tool_run_id for tool in tools}
    (simulation_id,) = tools[0].result.metadata.simulation_run_ids

    assert set(archive.find_tool_runs_of_simulation(simulation_id)) == run_ids
    assert archive.find_tool_runs_of_simulation("unknown_simulation") == []


def test_find_the_simulations_of_a_tool_run(
    archive_root, archive, manager, parameter_space
):
    """Check the way from a tool run to its simulations, the other way of the link:
    the summary and the result give the same ones, which are the simulations of
    the model archive."""
    tool, model = execute_doe(archive_root, parameter_space, manager)
    run_id = tool.result.metadata.tool_run_id

    (summary,) = archive.search_tool_runs()
    from_result = archive.get_tool_result(run_id).metadata.simulation_run_ids
    archived = {
        str(r["outputs"][MetaDataNames.run_id][0])
        for r in model.archive_manager.get_archived_results()
    }

    assert len(from_result) == N_SAMPLES
    assert set(summary["simulation_run_ids"]) == set(from_result) == archived


def test_failed_tool_run_is_archived_as_failed(archive_root, archive, manager):
    tool = FailingTool(archive_manager=manager, archive_root=archive_root)
    with pytest.raises(RuntimeError, match="boom"):
        tool.execute()

    (summary,) = archive.search_tool_runs()
    assert summary["status"] == "FAILED"
    assert summary["error"] == "RuntimeError: boom"
    with pytest.raises(KeyError, match="has no"):
        archive.get_tool_result(summary["tool_run_id"])
    assert archive.search_tool_runs(status="FAILED") == [summary]


def test_subtools_are_archived_with_their_parent(archive_root, archive, manager):
    sub_tool = MyTool(archive_manager=manager, archive_root=archive_root)
    composite = MyBaseCompositeTool(
        subtools=[sub_tool],
        archive_manager=manager,
        archive_root=archive_root,
    )
    composite.execute()

    composite_id = composite.result.metadata.tool_run_id
    sub_id = sub_tool.result.metadata.tool_run_id
    summaries = {run["tool_run_id"]: run for run in archive.search_tool_runs()}

    assert set(summaries) == {composite_id, sub_id}
    assert summaries[sub_id]["parent_tool_run_id"] == composite_id
    assert summaries[composite_id]["child_tool_run_ids"] == [sub_id]


def test_subtools_inherit_the_archive_of_their_parent(archive_root, archive, manager):
    """The subtools created without archive settings, as the composite tools do,
    archive their results with their parent, at any depth of nesting."""
    inner = MyBaseCompositeTool(name="inner", subtools=[MyTool()])
    outer = MyBaseCompositeTool(
        subtools=[inner], archive_manager=manager, archive_root=archive_root
    )
    outer.execute()

    names = {run["tool_name"] for run in archive.search_tool_runs()}
    assert names == {"MyBaseCompositeTool", "inner", "MyTool"}


def test_explicit_archive_settings_of_a_subtool_are_kept(
    archive_root, archive, manager
):
    sub_tool = MyTool(archive_manager="none")
    composite = MyBaseCompositeTool(
        subtools=[sub_tool],
        archive_manager=manager,
        archive_root=archive_root,
    )
    composite.execute()

    assert isinstance(sub_tool._tool_archive, NullToolArchive)
    (run,) = archive.search_tool_runs()
    assert run["tool_name"] == "MyBaseCompositeTool"


@pytest.mark.parametrize(
    "tool_class",
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
        partial(ResultFileReaderTool, "SpaceTool"),
    ],
    ids=lambda tool_class: getattr(tool_class, "__name__", "ResultFileReaderTool"),
)
def test_tools_with_their_own_constructor_accept_the_archive_settings(
    archive_root, tool_class
):
    """The tools defining their own constructor pass the archive settings to their
    base class, and to their subtools."""
    tool = tool_class(archive_manager="DirectoryArchive", archive_root=archive_root)

    for archived_tool in [tool, *getattr(tool, "_subtools", {}).values()]:
        assert isinstance(archived_tool._tool_archive, DirectoryToolArchive)
        assert archived_tool._tool_archive.root_directory == str(
            archive_root.absolute()
        )


def test_an_error_of_the_archive_does_not_lose_the_result(
    archive_root, parameter_space, monkeypatch, caplog
):
    def fail(self, result):
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(DirectoryToolArchive, "publish_tool_result", fail)
    with caplog.at_level(logging.ERROR):
        tool, _ = execute_doe(archive_root, parameter_space)

    assert tool.result.dataset is not None
    assert "could not be archived" in caplog.text
    assert "disk full" in caplog.text


def test_tool_archive_is_disabled_in_the_tests(tmp_wd):
    """Check the fixture of the tests, which relies on the configuration."""
    assert isinstance(MyTool()._tool_archive, NullToolArchive)
    assert not (tmp_wd / "default_archive").exists()


def test_archive_manager_comes_from_the_configuration(tmp_wd, monkeypatch):
    monkeypatch.setattr(config, "tool_archive_manager", "DirectoryArchive")
    assert isinstance(MyTool()._tool_archive, DirectoryToolArchive)

    # Without ``tool_archive_manager``, it is the one of the simulations.
    monkeypatch.setattr(config, "tool_archive_manager", None)
    monkeypatch.setattr(config, "run_archive_manager", "DirectoryArchive")
    assert isinstance(MyTool()._tool_archive, DirectoryToolArchive)

    # The setting of the tool takes precedence over the configuration.
    assert isinstance(MyTool(archive_manager="none")._tool_archive, NullToolArchive)


def test_default_archive_root(tmp_wd):
    archive = MyTool(archive_manager="DirectoryArchive")._tool_archive
    assert archive.root_directory == str((tmp_wd / "default_archive").absolute())

    archive = MyTool(
        archive_manager="DirectoryArchive", archive_root=tmp_wd / "other"
    )._tool_archive
    assert archive.root_directory == str((tmp_wd / "other").absolute())


def test_unknown_archive_manager():
    with pytest.raises(ValueError, match="Unknown archive manager"):
        open_tool_archive("Unknown", "root")


def test_mlflow_runs_of_subtools_are_nested(archive_root):
    """In MLflow, the run of a subtool is nested in the run of its parent tool, in a
    single experiment."""
    pytest.importorskip("mlflow")
    sub_tool = MyTool(archive_manager="MlflowArchive", archive_root=archive_root)
    composite = MyBaseCompositeTool(
        subtools=[sub_tool], archive_manager="MlflowArchive", archive_root=archive_root
    )
    composite.execute()

    archive = open_tool_archive("MlflowArchive", archive_root)
    summaries = {run["tool_run_id"]: run for run in archive.search_tool_runs()}
    parent = summaries[composite.result.metadata.tool_run_id]
    child = summaries[sub_tool.result.metadata.tool_run_id]
    child_run = archive._client.get_run(child["mlflow_run_id"])
    assert child_run.data.tags["mlflow.parentRunId"] == parent["mlflow_run_id"]
    assert child_run.info.experiment_id == archive.experiment_id
    # The result is also reachable from the id of its MLflow run.
    assert_results_equal(
        sub_tool.result,
        archive.get_tool_result_of_mlflow_run(child["mlflow_run_id"]),
    )


def test_mlflow_result_published_again(archive_root, parameter_space):
    """A result completed after the execution of the tool, then published again,
    replaces the archived one."""
    pytest.importorskip("mlflow")
    tool, _ = execute_doe(archive_root, parameter_space, "MlflowArchive")
    tool.result.metadata.misc["completed"] = True
    tool._republish_result()

    archive = open_tool_archive("MlflowArchive", archive_root)
    loaded = archive.get_tool_result(tool.result.metadata.tool_run_id)
    assert loaded.metadata.misc["completed"]
    (summary,) = archive.search_tool_runs()
    assert summary["status"] == "FINISHED"


def test_openturns_settings_are_described_in_clear(archive_root, archive, manager):
    """The prior of a Bayesian analysis, an OpenTURNS distribution, is described in
    clear in the summary of the tool run, not by the address of a Python object."""
    tool = BayesTool(archive_manager=manager, archive_root=archive_root)
    tool.execute(
        likelihood_dist="Normal",
        prior_dist=ComposedDistribution([Uniform(0, 5)] * 2),
        data=array([1.0, 2.0, 3.0]),
        n_mcmc=2,
    )

    (summary,) = archive.search_tool_runs()
    prior = summary["settings"]["prior_dist"]
    assert "Swig" not in str(prior)
    if manager == "MlflowArchive":
        # An MLflow parameter, in short form.
        assert prior.startswith("ComposedDistribution(Uniform(a = 0, b = 5)")
    else:
        assert prior["kind"] == "joint"
        assert prior["marginals"][0]["settings"]["name"] == "Uniform"


def _create_mlflow_model(archive_root):
    """A model whose simulations are in the MLflow database of the tool runs."""
    return create_model(
        "MockModel",
        "LC1",
        archive_manager="MlflowArchive",
        directory_archive_root=archive_root,
    )


def _get_simulation_runs(archive, model):
    """Return the MLflow runs of the simulations of a model."""
    experiment = archive._client.get_experiment_by_name(
        f"{model.name}_{model.load_case.name}"
    )
    return archive._client.search_runs([experiment.experiment_id])


def test_mlflow_tool_runs_are_linked_to_their_simulations(archive_root):
    """The tool run links to its simulations, and the simulations to the tool runs
    which used them, including from the cache of the model."""
    pytest.importorskip("mlflow")
    model = _create_mlflow_model(archive_root)
    input_dataset = generate_dataset(
        {IODataset.INPUT_GROUP: [Variable("x1", 0.5, is_constant_value=True)]}, 2
    )
    tools = [
        CustomDOETool(archive_manager="MlflowArchive", archive_root=archive_root)
        for _ in range(2)
    ]
    for tool in tools:
        tool.execute(model=model, input_dataset=input_dataset, output_names=["y1"])
    first_id, second_id = (tool.result.metadata.tool_run_id for tool in tools)

    archive = open_tool_archive("MlflowArchive", archive_root)
    (simulation,) = _get_simulation_runs(archive, model)
    # The second tool run retrieved the simulation from the cache: it is linked too.
    assert json.loads(simulation.data.tags["vimseo.tool_run_ids"]) == [
        first_id,
        second_id,
    ]
    experiment_id = simulation.info.experiment_id
    found = archive._client.search_runs(
        [experiment_id],
        filter_string=f"tags.`vimseo.tool_run_ids` LIKE '%{second_id}%'",
    )
    assert [run.info.run_id for run in found] == [simulation.info.run_id]

    summaries = {run["tool_run_id"]: run for run in archive.search_tool_runs()}
    description = archive._client.get_run(
        summaries[second_id]["mlflow_run_id"]
    ).data.tags["mlflow.note.content"]
    assert f"#/experiments/{experiment_id}/runs/{simulation.info.run_id}" in description
    assert "1 simulations" in description


def test_mlflow_subtool_runs_are_linked(archive_root):
    """The description of a tool run links to its parent and to its subtools."""
    pytest.importorskip("mlflow")
    sub_tool = MyTool(archive_manager="MlflowArchive", archive_root=archive_root)
    composite = MyBaseCompositeTool(
        subtools=[sub_tool], archive_manager="MlflowArchive", archive_root=archive_root
    )
    composite.execute()

    archive = open_tool_archive("MlflowArchive", archive_root)
    summaries = {run["tool_run_id"]: run for run in archive.search_tool_runs()}
    parent = summaries[composite.result.metadata.tool_run_id]["mlflow_run_id"]
    child = summaries[sub_tool.result.metadata.tool_run_id]["mlflow_run_id"]

    def description(run_id):
        return archive._client.get_run(run_id).data.tags["mlflow.note.content"]

    assert f"/runs/{child})" in description(parent)
    assert f"/runs/{parent})" in description(child)


def test_mlflow_tool_run_without_simulation(archive_root):
    """A tool run without model nor simulation has a description without link."""
    pytest.importorskip("mlflow")
    tool = BayesTool(archive_manager="MlflowArchive", archive_root=archive_root)
    tool.execute(
        likelihood_dist="Normal",
        prior_dist=ComposedDistribution([Uniform(0, 5)] * 2),
        data=array([1.0, 2.0, 3.0]),
        n_mcmc=2,
    )
    archive = open_tool_archive("MlflowArchive", archive_root)
    (summary,) = archive.search_tool_runs()
    description = archive._client.get_run(summary["mlflow_run_id"]).data.tags[
        "mlflow.note.content"
    ]
    assert "simulations" not in description


def test_mlflow_tool_run_without_model_linked_to_simulations(
    archive_root, parameter_space
):
    """A design value has no model in its result, but the simulations of its DOE are
    linked to it: they are searched in all the experiments."""
    pytest.importorskip("mlflow")
    model = _create_mlflow_model(archive_root)
    tool = DesignValueTool(archive_manager="MlflowArchive", archive_root=archive_root)
    tool.execute(
        inputs=DesignValueInputs(model=model, parameter_space=parameter_space),
        settings=DesignValueSettings(output_names=["y1"], n_samples=N_SAMPLES),
    )
    assert tool.result.metadata.model is None

    archive = open_tool_archive("MlflowArchive", archive_root)
    (summary,) = archive.search_tool_runs(tool_name="DesignValueTool")
    description = archive._client.get_run(summary["mlflow_run_id"]).data.tags[
        "mlflow.note.content"
    ]
    simulations = _get_simulation_runs(archive, model)
    assert len(simulations) == N_SAMPLES
    for simulation in simulations:
        assert f"/runs/{simulation.info.run_id})" in description
        assert summary["tool_run_id"] in json.loads(
            simulation.data.tags["vimseo.tool_run_ids"]
        )


def test_key_values_are_archived(archive_root, archive, manager, parameter_space):
    """The numbers summarizing a result are in the summary of its tool run, and are
    MLflow metrics."""
    execute_doe(archive_root, parameter_space, manager)
    (summary,) = archive.search_tool_runs()
    assert summary["key_values"] == {"n_samples": N_SAMPLES}
    if manager == "MlflowArchive":
        run = archive._client.get_run(summary["mlflow_run_id"])
        assert run.data.metrics == {"n_samples": N_SAMPLES}
