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

import pytest
from numpy import atleast_1d

from vimseo.api import create_model
from vimseo.utilities.cache_manipulator import cache_delete_entry
from vimseo.utilities.cache_viewer import cache_viewer


@pytest.fixture
def prepare_model_with_two_cache_entries():
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    model.execute({"x1": atleast_1d(-0.5)})
    return model


def test_cache_viewer(tmp_wd, prepare_model_with_two_cache_entries):
    """Check that the cache viewer util returns expected dataframe."""
    model = prepare_model_with_two_cache_entries
    nb_metadata_vars = len(list(model.get_metadata_names()))

    df = cache_viewer(model._cache_file_path)
    assert df.shape == (2, 5 + nb_metadata_vars)

    df = cache_viewer(model._cache_file_path, show_metadata_only=True)
    assert df.shape == (2, nb_metadata_vars)

    df = cache_viewer(model._cache_file_path, show_scalars_only=True)
    assert df.shape == (2, 5 + nb_metadata_vars)


def test_cache_entry_delete(tmp_wd, prepare_model_with_two_cache_entries):
    """Check that the cache entry delete utils correctly deletes a cache entry, and that
    the manipulated cache can be reused by another model instance."""
    model = prepare_model_with_two_cache_entries
    nb_metadata_vars = len(list(model.get_metadata_names()))

    cache_delete_entry(model._cache_file_path, 1)

    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    df = cache_viewer(model._cache_file_path)
    assert df.shape == (1, 5 + nb_metadata_vars)
