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

"""Tests of the error messages of the factories (#73)."""

from __future__ import annotations

import re

import pytest

from vimseo.api import create_model
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.factory import create_instance
from vimseo.core.factory import get_class
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_factory import ModelFactory


class _FactoryWithFailedImports:
    """A factory whose modules failed to import."""

    class_names = ("A", "B")
    failed_imports = {  # ruff: ignore[mutable-class-default]
        "pkg.short": "No module named 'foo'",
        "pkg.long": "cannot import name 'bar' from 'pkg.baz' (" + "x" * 300 + ")",
        "pkg.multiline": "first line\nsecond line",
    }

    def get_class(self, name: str) -> type:
        msg = name
        raise ImportError(msg)


def test_failed_imports_in_message():
    """Check that the failed imports are listed with the first line of their error,
    without truncating it."""
    with pytest.raises(ImportError) as info:
        get_class(_FactoryWithFailedImports(), "C", "model")
    message = str(info.value)
    assert message.endswith(
        "These modules could not be imported, so the classes they define are not "
        "available: pkg.short: No module named 'foo'; "
        "pkg.long: cannot import name 'bar' from 'pkg.baz' (" + "x" * 300 + "); "
        "pkg.multiline: first line [...]."
    )


@pytest.mark.parametrize(
    "factory_class", [ModelFactory, LoadCaseFactory, ComponentFactory]
)
def test_searched_packages_exist(factory_class):
    """Check that the packages searched by a factory exist, otherwise their import
    failure is listed in every error message of the factory."""
    package_names = factory_class._PACKAGE_NAMES
    failed_imports = factory_class().failed_imports
    assert not set(package_names) & set(failed_imports)


def test_unknown_model():
    """Check that an unknown model is explained."""
    with pytest.raises(ImportError, match=r"The model Foo is not available\. ") as info:
        create_model("Foo", "LC1")
    message = str(info.value)
    assert "subclass of IntegratedModel" in message
    assert "MockModel" in message
    # The base classes are not models to create.
    assert "IntegratedModel," not in message


def test_unknown_load_case():
    """Check that an unknown load case is explained."""
    with pytest.raises(ImportError, match=r"The load case Foo is not available\. "):
        create_model("MockModel", "Foo")


def test_load_case_of_another_model():
    """Check that a load case without component lists the load cases of the model."""
    with pytest.raises(
        ImportError,
        match=re.escape(
            "The component MockPre_Dummy is not available. The component of family "
            "MockPre for the load case Dummy must be a subclass of BaseComponent named "
            "MockPre_Dummy, i.e. {Family}_{LoadCase}. The available ones are: "
            "MockPre_LC1, MockPre_LC2."
        ),
    ):
        create_model("MockModel", "Dummy")


def test_component_with_wrong_arguments():
    """Check that a component not accepting its arguments raises an explicit error,
    instead of returning ``None``."""
    load_case = LoadCaseFactory().create("LC1")
    with pytest.raises(
        TypeError,
        match=r"The component MockPre_LC1 cannot be created .*unexpected keyword "
        r"argument 'foo'\. Check that its constructor",
    ):
        ComponentFactory().create("MockPre", load_case=load_case, foo=1)


class _OldSignature:
    def __init__(self, load_case_name: str) -> None:
        pass


def test_create_instance():
    """Check the error raised when a constructor does not accept its arguments."""
    assert isinstance(create_instance(_OldSignature, "model", "", "LC1"), _OldSignature)
    with pytest.raises(
        TypeError,
        match=re.escape(
            "The model _OldSignature cannot be created with the positional arguments "
            "['LC1'] and the keyword arguments ['load_case']: "
        ),
    ) as info:
        create_instance(_OldSignature, "model", "", "LC1", load_case=None)
    assert isinstance(info.value.__cause__, TypeError)


def test_model_factory_creates_a_model(tmp_wd):
    """Check that the model factory still creates a model."""
    model = ModelFactory().create("MockModel", "LC1")
    assert model.load_case.name == "LC1"
