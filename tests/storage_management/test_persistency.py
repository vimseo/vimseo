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
from pathlib import Path

import pytest
from gemseo.core.discipline.discipline import Discipline
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.problems.mock.mock_model_persistent.mock_model_persistent import (
    MockComponentStandalonePersistent_LC1,
)
from vimseo.storage_management.base_storage_manager import PersistencyPolicy


@pytest.mark.parametrize("persistency_policy", list(PersistencyPolicy))
@pytest.mark.parametrize("persistency_subject", ["scratch", "archive"])
def test_dir_persistency_policy_enforcement(
    tmp_wd, persistency_policy, persistency_subject
):
    """Test data persistency of models, as prescribed by the persistency policy at model
    construction."""

    model_name = "MockModelPersistent"
    load_case_name = "LC1"

    if persistency_subject == "scratch":
        attr_storage = "_scratch_manager"
        arg_persistency = "directory_scratch_persistency"
    elif persistency_subject == "archive":
        attr_storage = "archive_manager"
        arg_persistency = "directory_archive_persistency"
    else:
        raise NotImplementedError(persistency_subject)

    m = create_model(
        model_name,
        load_case_name,
        check_subprocess=False,
        **{arg_persistency: persistency_policy},
    )
    m.EXTRA_INPUT_GRAMMAR_CHECK = True
    m.set_cache(Discipline.CacheType.NONE)

    m.execute()

    # Checks whether the job dir exists, as prescribed by the persistency policy
    storage = getattr(m, attr_storage)
    job_dir_path = storage.job_directory
    policy = storage._persistency
    if job_dir_path is not None:
        if policy == PersistencyPolicy.DELETE_ALWAYS:
            assert not job_dir_path.is_dir()
        elif (
            policy == PersistencyPolicy.DELETE_NEVER
            or policy == PersistencyPolicy.DELETE_IF_FAULTY
        ):
            assert job_dir_path.is_dir()
        elif policy == PersistencyPolicy.DELETE_IF_SUCCESSFUL:
            assert not job_dir_path.is_dir()
        else:
            raise NotImplementedError(policy)

    # checks if _PERSISTENT_FILE_NAMES are actually copied to archive
    archive = m.archive_manager.job_directory
    if archive is not None and archive.is_dir():
        for file_name in m.archive_manager.persistent_file_names:
            if file_name != "":
                assert Path(m.archive_manager.job_directory / file_name).is_file()


@pytest.mark.parametrize("verif_mode", ["check_creation", "check_deletion"])
@pytest.mark.parametrize("job_name_spec", [True, False])
@pytest.mark.parametrize("job_dirs_spec", [True, False])
def test_dir_arg_specifications(tmp_wd, verif_mode, job_name_spec, job_dirs_spec):
    """Checks if model argument of name specification are enforced."""

    arg_dict = {}

    if job_name_spec:
        arg_dict.update({"job_name": "specified_job"})
    else:
        # leave default job_name naming
        pass

    if job_dirs_spec:
        arg_dict.update({"directory_scratch_root": "specified_scratch/foo"})
        arg_dict.update({"directory_archive_root": "specified_archive/bar"})
    else:
        # leave default job dir naming
        pass

    if verif_mode == "check_creation":
        # do not delete the job dirs, in order to check their existence
        arg_dict.update(
            directory_archive_persistency=PersistencyPolicy.DELETE_NEVER,
            directory_scratch_persistency=PersistencyPolicy.DELETE_NEVER,
        )
    elif verif_mode == "check_deletion":
        # do delete the job dirs, in order to check the deletion logic
        arg_dict.update(
            directory_archive_persistency=PersistencyPolicy.DELETE_ALWAYS,
            directory_scratch_persistency=PersistencyPolicy.DELETE_ALWAYS,
        )
    else:
        raise NotImplementedError(verif_mode)

    m = create_model(
        "MockModelPersistent",
        "LC1",
        check_subprocess=True,
        **arg_dict,
    )
    m.EXTRA_INPUT_GRAMMAR_CHECK = True
    m.set_cache(Discipline.CacheType.NONE)

    m.execute()

    if job_dirs_spec:
        expected_scratch_dir = Path("specified_scratch/foo")
        expected_archive_dir = Path("specified_archive/bar")
    else:
        expected_scratch_dir = Path("default_scratch/")
        expected_archive_dir = Path("default_archive/")

    archive_job_name = (
        "specified_job"
        if job_name_spec
        else (
            "none_file"
            if m.archive_manager.job_directory is None
            else m.archive_manager.job_directory.name
        )
    )
    expected_archive_dir = (
        expected_archive_dir
        / (f"{m.__class__.__name__}/{m.load_case.name}")
        / archive_job_name
    )

    scratch_job_name = (
        "specified_job"
        if job_name_spec
        else (
            "none_file"
            if m.scratch_job_directory is None
            else m.scratch_job_directory.name
        )
    )
    expected_scratch_dir = (
        expected_scratch_dir / (f"{m.name}/{m.load_case.name}") / scratch_job_name
    )

    if verif_mode == "check_creation":
        should_exist = True
    elif verif_mode == "check_deletion":
        should_exist = False
    else:
        raise NotImplementedError(verif_mode)

    scratch_file = expected_scratch_dir / "green_ellipse.png"
    assert scratch_file.is_file() == should_exist

    archive_file = expected_archive_dir / "results.json"
    assert archive_file.is_file() == should_exist


@pytest.mark.parametrize("job_name_spec", [True, False])
@pytest.mark.parametrize("use_cache", [True, False])
def test_re_execution_incremental(tmp_wd, job_name_spec, use_cache):
    """Checks whether consecutive execution works, with respect with the expected
    overwriting behaviour."""

    m = create_model(
        "MockModelPersistent",
        "LC1",
        check_subprocess=True,
        job_name="specified_job" if job_name_spec else "",
    )
    m.EXTRA_INPUT_GRAMMAR_CHECK = True
    if use_cache:
        m.set_cache(Discipline.CacheType.HDF5)
    else:
        m.set_cache(Discipline.CacheType.NONE)

    # first execution
    m.execute()

    expected_archive_name = "specified_job" if job_name_spec else "1"
    assert m.archive_manager.job_directory.name == expected_archive_name

    # second execution
    try:
        m.execute()
    except FileExistsError:
        # Direct re-execution a model with a specified job directory is not tolerated
        # because of archive over-writing
        assert job_name_spec is True

    expected_archive_name = (
        "specified_job" if job_name_spec else ("1" if use_cache else "2")
    )
    assert m.archive_manager.job_directory.name == expected_archive_name


def test_cache_from_archive(tmp_wd):
    """Check that the model cache can be set from an archive.

    Also check that the cache from archive is equal to the current model cache.
    """
    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    saved_cache = deepcopy(model.cache)
    model.create_cache_from_archive()

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

    # Check that we pass in the cache if the model is re-executed:
    model.execute()
    print(model.archive_manager.get_archived_results())
    assert len(model.archive_manager.get_archived_results()) == 1


def test_persistent_file_names(tmp_wd):
    """Check that storage archive correctly stores the filenames to be persisted."""

    # Persisting filename defined in ``_PERSISTENT_FILE_NAMES`` attribute.
    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    assert (
        model.archive_manager.persistent_file_names
        == MockComponentStandalonePersistent_LC1._PERSISTENT_FILE_NAMES
    )

    # Persisting filenames from fields.
    model = create_model("MockModelFields", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    assert model.archive_manager.persistent_file_names == ["Pyramid.vtk"]


def test_copy_of_fields(tmp_wd):
    """Check that fields are copied to the archive, and that the paths to the field files
    stored in the output_data are correct."""
    model = create_model("MockModelFields", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.cache = None
    output_data = model.execute()
    assert (model.archive_manager.job_directory / "Pyramid.vtk").exists()
    assert (
        Path(output_data[MetaDataNames.directory_archive_job][0])
        / output_data["pyramid"][0]
        == model.archive_manager.job_directory / "Pyramid.vtk"
    )
