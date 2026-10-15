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

import logging
from logging import _nameToLevel
from typing import ClassVar

from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.api import get_available_load_cases
from vimseo.api import get_available_models
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.problems.load_cases import DUMMY_LOAD_CASE_NAME


def _check_subprocess_flags(model):
    """The ``check_subprocess`` flag as seen by the model components."""
    return [
        d._check_subprocess
        for d in model._chain.disciplines
        if hasattr(d, "_check_subprocess")
    ]


def test_create_model_merges_model_options_and_kwargs(tmp_wd):
    """``model_options`` and loose keyword options are merged, not rejected."""
    cache_path = tmp_wd / "merged_cache.hdf"
    model = create_model(
        "MockModel",
        "LC1",
        check_subprocess=True,
        model_options=IntegratedModelSettings(cache_file_path=cache_path),
    )

    # the field from ``model_options`` is applied ...
    assert model._cache_file_path == cache_path
    # ... and so is the loose keyword option
    flags = _check_subprocess_flags(model)
    assert flags
    assert all(flags)


def test_create_model_kwarg_overrides_model_options(tmp_wd):
    """A loose keyword option wins over the same field of ``model_options``."""
    model = create_model(
        "MockModel",
        "LC1",
        check_subprocess=False,
        model_options=IntegratedModelSettings(
            check_subprocess=True, cache_file_path=tmp_wd / "c.hdf"
        ),
    )

    assert not any(_check_subprocess_flags(model))


def test_available_load_cases(tmp_wd):
    """Check the load cases available for a model."""
    assert get_available_load_cases("MockModel") == ["LC1", "LC2"]
    assert get_available_load_cases("BendingTestAnalytical") == [
        "Cantilever",
        "ThreePoints",
    ]


def test_available_models(tmp_wd):
    """Check that the models associated with a given load case are correctly found."""
    assert set(get_available_models("LC1")) == {
        "MockModel",
        "MockModelFields",
        "MockModelPersistent",
        "MockModelWithMaterial",
        "MockExternalSoftware",
        "MockModelSleep",
        "MockFaultyRunPost",
    }


def test_activate_logger_default_level(monkeypatch):
    """Without an explicit level, the VIMSEO configuration's own level is used."""
    from vimseo.config.global_configuration import _configuration as configuration

    calls = []
    monkeypatch.setattr(
        "gemseo.configure_logger", lambda **kwargs: calls.append(kwargs)
    )

    activate_logger()

    expected_level = _nameToLevel[configuration.logging.upper()]
    assert calls == [{"level": expected_level, "filename": "", "filemode": "a"}]


def test_activate_logger_explicit_level_and_file(tmp_wd, monkeypatch):
    """An explicit level and file are forwarded as is, not overridden."""
    calls = []
    monkeypatch.setattr(
        "gemseo.configure_logger", lambda **kwargs: calls.append(kwargs)
    )
    log_file = tmp_wd / "log.txt"

    activate_logger(level=logging.DEBUG, filename=log_file, filemode="w")

    assert calls == [{"level": logging.DEBUG, "filename": log_file, "filemode": "w"}]


def test_activate_logger_real_call_smoke():
    """A real, non-mocked call configures the logger without raising."""
    activate_logger(logging.INFO)


def test_create_model_with_material_and_model_options_together(tmp_wd):
    """``material``, ``model_options`` and a loose kwarg can all be combined."""
    cache_path = tmp_wd / "c.hdf"
    model = create_model(
        "BendingTestAnalytical",
        "Cantilever",
        material="Ta6v_annealed",
        model_options=IntegratedModelSettings(cache_file_path=cache_path),
        check_subprocess=True,
    )

    assert model.material.name == "Ta6v_annealed"
    assert model._cache_file_path == cache_path
    flags = _check_subprocess_flags(model)
    assert flags
    assert all(flags)


def test_get_available_load_cases_skips_dummy_load_case(monkeypatch):
    """The dummy placeholder load case is never offered as a real choice."""

    class _FakeLoadCase:
        def __init__(self, name):
            self.name = name

    class _FakeLoadCaseFactory:
        class_names: ClassVar[list[str]] = [DUMMY_LOAD_CASE_NAME]

        def create(self, class_name, domain=""):
            return _FakeLoadCase(class_name)

    monkeypatch.setattr(
        "vimseo.core.load_case_factory.LoadCaseFactory", _FakeLoadCaseFactory
    )

    assert get_available_load_cases("PreRunPostModel") == []


def test_get_available_load_cases_filters_by_component_family(tmp_wd):
    """Only the load cases wired to the model's own component family are kept."""
    assert get_available_load_cases("MockModelSleep") == ["LC1"]
