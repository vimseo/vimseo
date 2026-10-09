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

"""Tests of the identifiers of the simulations and of their link to the tool runs."""

from __future__ import annotations

import re

import pytest
from numpy import array

from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.run_context import current_tool_run
from vimseo.core.run_context import record_simulation
from vimseo.core.run_context import record_simulation_from_outputs
from vimseo.core.run_context import tool_run
from vimseo.problems.mock.mock_pre_run_post.mock_main import MockModel

HEX_ID = re.compile(r"^[0-9a-f]{32}$")


def run_id_of(outputs) -> str:
    return str(outputs[MetaDataNames.run_id][0])


def tool_run_id_of(outputs) -> str:
    return str(outputs[MetaDataNames.tool_run_id][0])


@pytest.fixture
def model(tmp_wd):
    model = MockModel("LC1")
    model.cache = None
    return model


def test_each_simulation_has_its_own_run_id(model):
    """Check that a simulation which is really run has a new unique identifier, and no
    tool run when it is not executed by a tool."""
    first = run_id_of(model.execute({"x1": array([0.1])}))
    second = run_id_of(model.execute({"x1": array([0.2])}))

    assert HEX_ID.match(first)
    assert HEX_ID.match(second)
    assert first != second
    assert tool_run_id_of(model.get_output_data()) == ""


def test_cached_simulation_keeps_its_run_id(tmp_wd):
    """Check that a result retrieved from the cache is not given a new identifier."""
    model = MockModel("LC1")
    first = run_id_of(model.execute({"x1": array([0.1])}))
    again = run_id_of(model.execute({"x1": array([0.1])}))
    other = run_id_of(model.execute({"x1": array([0.3])}))

    assert again == first
    assert other != first


def test_run_id_is_archived(model):
    """Check that the identifiers are stored in the archive of the simulation."""
    outputs = model.execute({"x1": array([0.1])})
    results = model.archive_manager.get_archived_results()

    assert len(results) == 1
    assert results[0]["outputs"][MetaDataNames.run_id][0] == run_id_of(outputs)
    assert results[0]["outputs"][MetaDataNames.tool_run_id][0] == ""


def test_simulation_in_a_tool_run_has_its_tool_run_id(model):
    with tool_run("a_tool") as run:
        outputs = model.execute({"x1": array([0.1])})

    assert tool_run_id_of(outputs) == run.tool_run_id
    assert list(run.simulation_run_ids) == [run_id_of(outputs)]
    assert current_tool_run() is None


def test_cached_simulation_is_recorded_by_the_tool_run_using_it(tmp_wd):
    """Check that a tool run using a cached simulation records it, while the
    simulation keeps the tool run which created it."""
    model = MockModel("LC1")
    with tool_run("first_tool") as first_run:
        first = model.execute({"x1": array([0.1])})
    with tool_run("second_tool") as second_run:
        second = model.execute({"x1": array([0.1])})

    assert run_id_of(second) == run_id_of(first)
    assert list(second_run.simulation_run_ids) == list(first_run.simulation_run_ids)
    assert tool_run_id_of(second) == first_run.tool_run_id
    assert first_run.tool_run_id != second_run.tool_run_id


def test_nested_tool_runs():
    """Check that a tool run is the child of the one executing it, and that its
    simulations are also those of its parent."""
    with tool_run("parent") as parent:
        record_simulation("sim_0")
        with tool_run("child_1") as child_1:
            record_simulation("sim_1")
            record_simulation("sim_1")
        with tool_run("child_2") as child_2:
            record_simulation("sim_2")
            record_simulation("sim_0")

    assert child_1.parent is parent
    assert parent.parent is None
    assert parent.child_tool_run_ids == [child_1.tool_run_id, child_2.tool_run_id]
    assert list(child_1.simulation_run_ids) == ["sim_1"]
    assert list(child_2.simulation_run_ids) == ["sim_2", "sim_0"]
    assert list(parent.simulation_run_ids) == ["sim_0", "sim_1", "sim_2"]


def test_recording_outside_a_tool_run_does_nothing():
    record_simulation("sim")
    record_simulation_from_outputs({MetaDataNames.run_id: array(["sim"])})
    assert current_tool_run() is None


def _failing_tool_run():
    with tool_run("failing_tool"):
        msg = "boom"
        raise RuntimeError(msg)


def test_tool_run_is_closed_after_an_error():
    with pytest.raises(RuntimeError, match="boom"):
        _failing_tool_run()
    assert current_tool_run() is None


def test_outputs_without_run_id_are_not_recorded():
    """Check the outputs of a model whose outputs were restricted by a formulation."""
    with tool_run("a_tool") as run:
        record_simulation_from_outputs({"y1": array([1.0])})
    assert len(run.simulation_run_ids) == 0
