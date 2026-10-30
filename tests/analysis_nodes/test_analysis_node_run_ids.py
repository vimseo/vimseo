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

"""Tests of the link between an analysis node result and the simulations it used."""

from __future__ import annotations

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset

from vimseo.analysis_nodes.doe.custom_doe import CustomDOEAnalysisNode
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNode
from vimseo.analysis_nodes.mock.mock_analysis_node import MyBaseCompositeAnalysisNode
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.run_context import current_analysis_node_run
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import generate_dataset

N_SAMPLES = 4


@pytest.fixture
def parameter_space():
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, minimum=-1.0, maximum=1.0
    )
    return parameter_space


def archived_simulations(model) -> dict[str, str]:
    """Return the ``analysis_node_run_id`` of each archived simulation, by ``run_id``."""
    return {
        str(result["outputs"][MetaDataNames.run_id][0]): str(
            result["outputs"][MetaDataNames.analysis_node_run_id][0]
        )
        for result in model.archive_manager.get_archived_results()
    }


def test_doe_result_is_linked_to_its_simulations(tmp_wd, parameter_space):
    """Check both directions of the link: the analysis node result lists the simulations,
    and each simulation holds the analysis node run."""
    model = MockModel("LC1")
    model.cache = None
    doe_analysis_node = DOEAnalysisNode()
    result = doe_analysis_node.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )

    metadata = result.metadata
    assert len(metadata.analysis_node_run_id) == len("20261019T104610_e5c1a9d7")
    assert metadata.parent_analysis_node_run_id == ""
    assert metadata.child_analysis_node_run_ids == ()
    assert len(metadata.simulation_run_ids) == N_SAMPLES

    simulations = archived_simulations(model)
    assert set(metadata.simulation_run_ids) == set(simulations)
    assert set(simulations.values()) == {metadata.analysis_node_run_id}
    assert current_analysis_node_run() is None


def test_two_executions_of_an_analysis_node_have_different_run_ids(
    tmp_wd, parameter_space
):
    model = MockModel("LC1")
    model.cache = None
    doe_analysis_node = DOEAnalysisNode()
    options = {
        "model": model,
        "parameter_space": parameter_space,
        "output_names": ["y1"],
        "algo": "OT_OPT_LHS",
        "n_samples": N_SAMPLES,
    }
    first = doe_analysis_node.execute(**options).metadata
    first_run_id, first_simulations = (
        first.analysis_node_run_id,
        first.simulation_run_ids,
    )
    second = doe_analysis_node.execute(**options).metadata

    assert second.analysis_node_run_id != first_run_id
    assert set(second.simulation_run_ids).isdisjoint(first_simulations)


def test_simulations_used_by_two_analysis_nodes_are_shared(tmp_wd):
    """Check that an analysis node using simulations found in the model cache lists them, while
    the simulations still refer to the analysis node run which created them."""
    model = MockModel("LC1")
    input_dataset = generate_dataset(
        {IODataset.INPUT_GROUP: [Variable("x1", 0.5, is_constant_value=True)]}, 3
    )

    first = CustomDOEAnalysisNode().execute(
        model=model, input_dataset=input_dataset, output_names=["y1"]
    )
    first_ids = first.metadata.simulation_run_ids
    first_run_id = first.metadata.analysis_node_run_id
    second = CustomDOEAnalysisNode().execute(
        model=model, input_dataset=input_dataset, output_names=["y1"]
    )

    assert second.metadata.analysis_node_run_id != first_run_id
    # The three samples are the same point: one simulation, used by both analysis nodes.
    assert len(first_ids) == 1
    assert second.metadata.simulation_run_ids == first_ids
    assert set(archived_simulations(model).values()) == {first_run_id}


def test_composite_analysis_node_links_its_sub_analysis_nodes(tmp_wd):
    sub_analysis_node = MyAnalysisNode()
    composite = MyBaseCompositeAnalysisNode(sub_analysis_nodes=[sub_analysis_node])
    composite.execute()

    composite_metadata = composite.result.metadata
    sub_metadata = sub_analysis_node.result.metadata
    assert composite_metadata.analysis_node_run_id != ""
    assert composite_metadata.parent_analysis_node_run_id == ""
    assert composite_metadata.child_analysis_node_run_ids == (
        sub_metadata.analysis_node_run_id,
    )
    assert (
        sub_metadata.parent_analysis_node_run_id
        == composite_metadata.analysis_node_run_id
    )


def test_run_ids_survive_hdf5(tmp_wd, parameter_space):
    model = MockModel("LC1")
    model.cache = None
    doe_analysis_node = DOEAnalysisNode()
    doe_analysis_node.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )
    doe_analysis_node.save_results()

    loaded = DOEAnalysisNode.load_results(
        doe_analysis_node.working_directory / "DOEAnalysisNode_result.hdf5"
    )

    assert (
        loaded.metadata.analysis_node_run_id
        == doe_analysis_node.result.metadata.analysis_node_run_id
    )
    assert (
        loaded.metadata.simulation_run_ids
        == doe_analysis_node.result.metadata.simulation_run_ids
    )
    assert isinstance(loaded.metadata.simulation_run_ids, tuple)
