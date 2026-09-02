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

"""Access to the dependencies shipped by the optional extras.

The mandatory dependencies of VIMSEO are kept to what is needed to build a model,
execute it and serialize its results, so that it can be installed on a machine with
no graphical stack, typically an HPC compute node. Everything else is shipped by an
extra, declared in the ``[project.optional-dependencies]`` table of ``pyproject.toml``:

| Extra | Brings | Used by |
| --- | --- | --- |
| ``dashboard`` | ``streamlit`` | [vimseo.dashboards][] |
| ``mlflow`` | ``mlflow`` | [MlflowArchive][vimseo.storage_management.mlflow_storage.MlflowArchive] |
| ``mesh`` | ``pyvista`` | [extract_line][vimseo.utilities.fields.extract_line] |
| ``jax`` | ``jax`` | [vimseo.lib_vimseo.tan_lib_jax][] |

Import the modules they provide with [import_optional][vimseo.utilities.optional_dependencies.import_optional]
so that a missing extra reports how to install it instead of raising a bare
``ModuleNotFoundError``.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

EXTRA_TO_DISTRIBUTIONS: dict[str, tuple[str, ...]] = {
    "dashboard": ("streamlit", "streamlit-pydantic-sebastienbocquet"),
    "mlflow": ("mlflow",),
    "mesh": ("pyvista",),
    "jax": ("jax", "jaxlib"),
}
"""The distributions brought by each extra, used for documentation and testing."""


def import_optional(module_name: str, extra: str, feature: str = "") -> ModuleType:
    """Import a module shipped by an optional extra.

    Args:
        module_name: The name of the module to import, e.g. ``"pyvista"``.
        extra: The name of the extra shipping it, e.g. ``"mesh"``.
        feature: The name of the VIMSEO feature requiring the module,
            used in the error message. If empty, the module name is used instead.

    Returns:
        The imported module.

    Raises:
        ImportError: If the module cannot be imported, with the command to install
            the extra shipping it.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as error:
        msg = (
            f"{feature or module_name} requires the optional dependency "
            f"'{module_name}', shipped by the '{extra}' extra. "
            f'Install it with: pip install "vimseo[{extra}]"'
        )
        raise ImportError(msg) from error
