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

"""Tests for :class:`.ModelComposition` (base model + post-processing components)."""

from __future__ import annotations

import pytest
from gemseo.core.grammars.errors import InvalidDataError
from numpy import atleast_1d

from vimseo.api import create_model
from vimseo.core.components.base_component import BaseComponent
from vimseo.core.model_settings import IntegratedModelSettings


def _make_post(base_model, extra_outputs=()):
    """Build a post-processing component that depends on the base model grammars.

    Mirrors the ``MyPost`` component of the ``plot_041_post_processing_patch``
    gallery example. ``extra_outputs`` lets a test declare additional output
    names, which is used to emulate a grammar change across code versions.
    """

    class _Post(BaseComponent):
        auto_detect_grammar_files = False
        default_grammar_type = "SimpleGrammar"

        def __init__(self, **options):
            super().__init__(**options)
            self.input_grammar.update_from_names(
                list(base_model.output_grammar.names)
                + list(base_model.input_grammar.names)
            )
            self.output_grammar.update_from_data({"relative_max_dplt": atleast_1d(0.0)})
            for name in extra_outputs:
                self.output_grammar.update_from_data({name: atleast_1d(0.0)})

        def _run(self, input_data):
            output_data = {
                "relative_max_dplt": input_data["dplt_at_force_location"]
                / input_data["length"]
            }
            for name in extra_outputs:
                output_data[name] = atleast_1d(0.0)
            return output_data

    return _Post()


def _make_composition(base_model, post, cache_file_path, tmp_path):
    return create_model(
        "BendingTestWithPost",
        "Cantilever",
        base_model=base_model,
        post_components=[post],
        model_options=IntegratedModelSettings(
            directory_archive_root=tmp_path / "archive",
            directory_scratch_root=tmp_path / "scratch",
            cache_file_path=cache_file_path,
        ),
    )


@pytest.mark.fast
def test_model_composition_output_contains_base_outputs(tmp_wd, tmp_path):
    """A fresh composition run exposes the base model outputs and the post output."""
    base_model = create_model("BendingTestAnalytical", "Cantilever")
    base_model.execute()

    composition = _make_composition(
        base_model, _make_post(base_model), tmp_path / "with_post.hdf", tmp_path
    )
    output = composition.execute()

    assert "relative_max_dplt" in output
    for name in base_model.get_output_data_names(remove_metadata=True):
        assert name in output, f"base output {name!r} missing from composition output"


@pytest.mark.fast
def test_model_composition_cache_hit_roundtrips_all_outputs(tmp_wd, tmp_path):
    """Re-executing a composition (cache hit) still returns every required output.

    On a cache hit GEMSEO skips ``_run`` and re-validates the restored ``io.data``
    against the output grammar; this guards that the cache stores the full output
    set (base outputs + post output), not just the post output.
    """
    base_model = create_model("BendingTestAnalytical", "Cantilever")
    base_model.execute()
    cache_file = tmp_path / "with_post.hdf"

    composition = _make_composition(
        base_model, _make_post(base_model), cache_file, tmp_path
    )
    composition.execute()

    # Identical inputs -> cache hit -> restored io.data re-validated.
    output = composition.execute()

    assert "relative_max_dplt" in output
    for name in base_model.get_output_data_names(remove_metadata=True):
        assert name in output


@pytest.mark.fast
def test_model_composition_stale_cache_raises(tmp_wd, tmp_path):
    """A cache written before the grammar gained an output fails to validate.

    An HDF cache produced by an
    older version of the model is missing outputs that the current output grammar
    requires. On the cache hit GEMSEO restores the stale (incomplete) data and the
    output-grammar validation raises.
    """
    cache_file = tmp_path / "with_post.hdf"

    # "Old code": the post declares only ``relative_max_dplt``; writes the cache.
    base_model = create_model("BendingTestAnalytical", "Cantilever")
    base_model.execute()
    old_composition = _make_composition(
        base_model, _make_post(base_model), cache_file, tmp_path
    )
    old_composition.execute()

    # "New code" sharing the same cache file: the post now also requires
    # ``extra_output``, which the cached entry does not contain.
    base_model_2 = create_model("BendingTestAnalytical", "Cantilever")
    base_model_2.execute()
    new_composition = _make_composition(
        base_model_2,
        _make_post(base_model_2, extra_outputs=("extra_output",)),
        cache_file,
        tmp_path,
    )

    with pytest.raises(InvalidDataError):
        new_composition.execute()
