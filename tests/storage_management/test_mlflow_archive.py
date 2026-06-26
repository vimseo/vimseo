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

from numpy.core.shape_base import atleast_1d
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings


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
    # directory_archive_job field is not relevant for Mlflow archive.
    tested_names = [
        name
        for name in model.get_output_data_names()
        if name != MetaDataNames.directory_archive_job
    ]
    for name in tested_names:
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
    # TODO Incoherency: directory_archive_job is not filled by the model,
    #  but is filled by method ``get_result()``
    #  of MlflowArchive. It creates a mismatch between cache outputs
    #  (in which directory_archive_job is filled
    #  through ``get_result()`` and the model outputs when the cache is not used.
    tested_names = [
        name
        for name in expected_dataset
        if name
        not in [
            MetaDataNames.date,
            MetaDataNames.cpu_time,
            MetaDataNames.directory_archive_job,
        ]
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
