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

"""Check that VIMSEO works with its mandatory dependencies only.

VIMSEO must install and run on a machine with no graphical stack, typically an HPC
compute node. Everything that cannot be installed there is shipped by an extra
declared in ``[project.optional-dependencies]``.

These tests are the guard rail of that split. They matter because GEMSEO swallows
import failures during class discovery: ``BaseFactory`` catches ``BaseException`` and
records the failure in ``failed_imports``. So an ``import pyvista`` added at the top of
a module of ``vimseo.tools`` would raise nothing -- the tool would simply vanish from
``get_available_tools()``, silently, and only for the users who installed the core.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path

import pytest
import tomllib

from vimseo.core.model_factory import ModelFactory
from vimseo.storage_management import get_archive_class
from vimseo.storage_management.directory_storage import DirectoryArchive
from vimseo.tools.tools_factory import ToolsFactory
from vimseo.utilities.optional_dependencies import EXTRA_TO_DISTRIBUTIONS
from vimseo.utilities.optional_dependencies import import_optional

EXTRA_TO_OPTIONAL_MODULES: dict[str, tuple[str, ...]] = {
    "dashboard": ("vimseo.dashboards",),
    "mlflow": ("vimseo.storage_management.mlflow_storage",),
    "jax": ("vimseo.lib_vimseo.tan_lib_jax",),
    # pyvista is imported lazily, inside extract_line() and vtu_to_png(), so no
    # module of the package may fail to import when the "mesh" extra is missing.
    "mesh": (),
}
"""The modules of ``vimseo`` allowed to fail to import when an extra is missing."""

DEV_ONLY_MODULES = frozenset({
    # Ships the pytest fixtures offered to the users of VIMSEO. pytest belongs to the
    # "dev" dependency group, not to the mandatory dependencies.
    "vimseo.utilities.pytest_conftest",
})

KNOWN_BROKEN_MODULES = frozenset({
    # Unrelated to the optional dependencies: the module imports
    # analytic_bending_test_analytical_cantilever, which no longer exists.
    "vimseo.problems.beam_explicit.reference_dataset_builder",
})

CORE_TOOLS = (
    "BayesTool",
    "CalibrationStep",
    "DOETool",
    "DesignValueTool",
    "DistributionComparison",
    "ReaderFileTecplot",
    "SensitivityTool",
    "SolutionVerificationCase",
    "StatisticsTool",
    "StochasticValidationPoint",
    "SurrogateTool",
)
"""Tools that must be discoverable without any extra installed."""

CORE_MODELS = (
    "BendingTestAnalytical",
    "PreRunPostModel",
    # meshio is mandatory, so TanOpenHole stays discoverable and instantiable on a
    # core install. Executing it is a separate story: see
    # test_tan_open_hole_execution_needs_mesh_extra() below.
    "TanOpenHole",
)
"""Models that must be discoverable, and their default instance buildable, without
any extra installed. This says nothing about whether *executing* them needs one."""


def _is_installed(extra: str) -> bool:
    """Whether the distributions shipped by an extra are importable."""
    module_names = {"streamlit-pydantic-sebastienbocquet": "streamlit_pydantic"}
    return all(
        importlib.util.find_spec(module_names.get(dist, dist.replace("-", "_")))
        is not None
        for dist in EXTRA_TO_DISTRIBUTIONS[extra]
    )


def _allowed_failures() -> set[str]:
    """The module prefixes allowed to fail, given the extras actually installed."""
    allowed = set(DEV_ONLY_MODULES) | set(KNOWN_BROKEN_MODULES)
    for extra, modules in EXTRA_TO_OPTIONAL_MODULES.items():
        if not _is_installed(extra):
            allowed.update(modules)
    return allowed


@pytest.mark.fast
@pytest.mark.parametrize("factory_class", [ToolsFactory, ModelFactory])
def test_no_core_module_fails_to_import(factory_class):
    """Check that only modules of a missing extra fail during class discovery."""
    allowed = _allowed_failures()
    unexpected = {
        name: error
        for name, error in factory_class().failed_imports.items()
        if name.startswith("vimseo")
        and not any(name == a or name.startswith(f"{a}.") for a in allowed)
    }
    assert not unexpected, (
        "These modules of the core failed to import, so the classes they define are "
        f"silently missing from {factory_class.__name__}: {unexpected}"
    )


@pytest.mark.fast
def test_core_tools_are_discoverable():
    """Check that the core tools are registered whatever the extras installed."""
    missing = set(CORE_TOOLS) - set(ToolsFactory().class_names)
    assert not missing


@pytest.mark.fast
def test_core_models_are_discoverable():
    """Check that the core models are registered whatever the extras installed."""
    missing = set(CORE_MODELS) - set(ModelFactory().class_names)
    assert not missing


@pytest.mark.fast
def test_tan_open_hole_execution_needs_mesh_extra():
    """TanOpenHole is a core model, but executing it is not core-only.

    Its ``PostFieldExtraction`` step reads the flux field it just wrote back with
    pyvista (line extraction), so ``execute()`` -- unlike ``create_model()`` --
    requires the ``mesh`` extra.
    """
    from vimseo.api import create_model

    model = create_model("TanOpenHole", "Tension")
    if _is_installed("mesh"):
        model.execute()
    else:
        with pytest.raises(ImportError, match=r'pip install "vimseo\[mesh\]"'):
            model.execute()


@pytest.mark.fast
def test_import_optional_reports_the_extra_to_install():
    """Check that a missing optional dependency tells how to install it."""
    with pytest.raises(ImportError, match=r'pip install "vimseo\[mesh\]"'):
        import_optional("a_module_that_is_not_installed", "mesh")


@pytest.mark.fast
def test_directory_archive_needs_no_extra():
    """Check that the default archive backend is available on a core install."""
    assert get_archive_class("DirectoryArchive") is DirectoryArchive


@pytest.mark.fast
def test_mlflow_archive_depends_on_its_extra():
    """Check how the MlflowArchive backend behaves with and without its extra."""
    if _is_installed("mlflow"):
        from vimseo.storage_management.mlflow_storage import MlflowArchive

        assert get_archive_class("MlflowArchive") is MlflowArchive
    else:
        with pytest.raises(ImportError, match=r'pip install "vimseo\[mlflow\]"'):
            get_archive_class("MlflowArchive")


@pytest.mark.fast
def test_unknown_archive_manager_is_rejected():
    """Check that an unknown archive manager name raises a readable error."""
    with pytest.raises(ValueError, match="Unknown archive manager"):
        get_archive_class("NotAnArchive")


@pytest.mark.fast
def test_declared_extras_match_the_documented_ones():
    """Check that EXTRA_TO_DISTRIBUTIONS stays in sync with pyproject.toml."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject.is_file():
        # Running against an installed distribution rather than the source tree.
        declared = set(importlib.metadata.metadata("vimseo").get_all("Provides-Extra"))
    else:
        content = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        declared = set(content["project"]["optional-dependencies"])
    # "all" is a convenience union, it ships no distribution of its own.
    assert declared - {"all"} == set(EXTRA_TO_DISTRIBUTIONS)
    assert declared - {"all"} == set(EXTRA_TO_OPTIONAL_MODULES)
