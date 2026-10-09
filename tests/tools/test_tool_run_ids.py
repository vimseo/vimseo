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

"""Tests of the link between a tool result and the simulations it used."""

from __future__ import annotations

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset

from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.run_context import current_tool_run
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.mock.mock_tool import MyBaseCompositeTool
from vimseo.tools.mock.mock_tool import MyTool
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
    """Return the ``tool_run_id`` of each archived simulation, by ``run_id``."""
    return {
        str(result["outputs"][MetaDataNames.run_id][0]): str(
            result["outputs"][MetaDataNames.tool_run_id][0]
        )
        for result in model.archive_manager.get_archived_results()
    }


def test_doe_result_is_linked_to_its_simulations(tmp_wd, parameter_space):
    """Check both directions of the link: the tool result lists the simulations,
    and each simulation holds the tool run."""
    model = MockModel("LC1")
    model.cache = None
    doe_tool = DOETool()
    result = doe_tool.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )

    metadata = result.metadata
    assert len(metadata.tool_run_id) == 32
    assert metadata.parent_tool_run_id == ""
    assert metadata.child_tool_run_ids == ()
    assert len(metadata.simulation_run_ids) == N_SAMPLES

    simulations = archived_simulations(model)
    assert set(metadata.simulation_run_ids) == set(simulations)
    assert set(simulations.values()) == {metadata.tool_run_id}
    assert current_tool_run() is None


def test_two_executions_of_a_tool_have_different_run_ids(tmp_wd, parameter_space):
    model = MockModel("LC1")
    model.cache = None
    doe_tool = DOETool()
    options = {
        "model": model,
        "parameter_space": parameter_space,
        "output_names": ["y1"],
        "algo": "OT_OPT_LHS",
        "n_samples": N_SAMPLES,
    }
    first = doe_tool.execute(**options).metadata
    first_run_id, first_simulations = first.tool_run_id, first.simulation_run_ids
    second = doe_tool.execute(**options).metadata

    assert second.tool_run_id != first_run_id
    assert set(second.simulation_run_ids).isdisjoint(first_simulations)


def test_simulations_used_by_two_tools_are_shared(tmp_wd):
    """Check that a tool using simulations found in the model cache lists them, while
    the simulations still refer to the tool run which created them."""
    model = MockModel("LC1")
    input_dataset = generate_dataset(
        {IODataset.INPUT_GROUP: [Variable("x1", 0.5, is_constant_value=True)]}, 3
    )

    first = CustomDOETool().execute(
        model=model, input_dataset=input_dataset, output_names=["y1"]
    )
    first_ids = first.metadata.simulation_run_ids
    first_run_id = first.metadata.tool_run_id
    second = CustomDOETool().execute(
        model=model, input_dataset=input_dataset, output_names=["y1"]
    )

    assert second.metadata.tool_run_id != first_run_id
    # The three samples are the same point: one simulation, used by both tools.
    assert len(first_ids) == 1
    assert second.metadata.simulation_run_ids == first_ids
    assert set(archived_simulations(model).values()) == {first_run_id}


def test_composite_tool_links_its_subtools(tmp_wd):
    sub_tool = MyTool()
    composite = MyBaseCompositeTool(subtools=[sub_tool])
    composite.execute()

    composite_metadata = composite.result.metadata
    sub_metadata = sub_tool.result.metadata
    assert composite_metadata.tool_run_id != ""
    assert composite_metadata.parent_tool_run_id == ""
    assert composite_metadata.child_tool_run_ids == (sub_metadata.tool_run_id,)
    assert sub_metadata.parent_tool_run_id == composite_metadata.tool_run_id


def test_run_ids_survive_hdf5(tmp_wd, parameter_space):
    model = MockModel("LC1")
    model.cache = None
    doe_tool = DOETool()
    doe_tool.execute(
        model=model,
        parameter_space=parameter_space,
        output_names=["y1"],
        algo="OT_OPT_LHS",
        n_samples=N_SAMPLES,
    )
    doe_tool.save_results()

    loaded = DOETool.load_results(doe_tool.working_directory / "DOETool_result.hdf5")

    assert loaded.metadata.tool_run_id == doe_tool.result.metadata.tool_run_id
    assert (
        loaded.metadata.simulation_run_ids
        == doe_tool.result.metadata.simulation_run_ids
    )
    assert isinstance(loaded.metadata.simulation_run_ids, tuple)
