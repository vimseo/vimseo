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

"""Tests of the search of the archived simulations from their run_id."""

from __future__ import annotations

import pytest
from numpy import array

from vimseo.api import create_model
from vimseo.api import load_simulation_results
from vimseo.core.model_metadata import MetaDataNames


@pytest.fixture(params=["DirectoryArchive", "MlflowArchive"])
def model(request, tmp_wd):
    """A model archiving its simulations, for each backend."""
    if request.param == "MlflowArchive":
        pytest.importorskip("mlflow")
    model = create_model(
        "MockModel",
        "LC1",
        archive_manager=request.param,
        directory_archive_root=tmp_wd / "archive",
    )
    model.cache = None
    return model


def _run_id(model, x1: float) -> str:
    output_data = model.execute({"x1": array([x1])})
    return str(output_data[MetaDataNames.run_id][0])


def test_get_results_by_run_id(model):
    """The simulations are found from their run_id, in the requested order, whatever
    their experiment."""
    first = _run_id(model, 1.0)
    model.archive_manager.set_experiment("another_experiment")
    second = _run_id(model, 0.5)

    results = model.archive_manager.get_results_by_run_id([second, first])

    assert [str(r["outputs"][MetaDataNames.run_id][0]) for r in results] == [
        second,
        first,
    ]
    assert [r["inputs"]["x1"][0] for r in results] == [0.5, 1.0]


def test_get_results_of_an_unknown_run_id(model):
    _run_id(model, 1.0)
    with pytest.raises(KeyError, match="No simulation with run_id"):
        model.archive_manager.get_results_by_run_id(["unknown"])


def test_load_simulation_results(model, tmp_wd):
    """The simulations are loaded without their model, as model results."""
    first = _run_id(model, 1.0)
    second = _run_id(model, 0.5)

    results = load_simulation_results(
        [second, first],
        archive_manager=model.archive_manager.__class__.__name__,
        archive_root=tmp_wd / "archive",
    )

    assert [result.metadata.report[MetaDataNames.run_id] for result in results] == [
        second,
        first,
    ]
    if model.archive_manager.__class__.__name__ == "MlflowArchive":
        # Opening the archive to read it creates no experiment.
        client = model.archive_manager._mlflow_client
        assert "_" not in {
            experiment.name for experiment in client.search_experiments()
        }
