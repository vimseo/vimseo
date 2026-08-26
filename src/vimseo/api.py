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
import warnings

from vimseo.problems.load_cases import DUMMY_LOAD_CASE_NAME

warnings.filterwarnings(
    "ignore",
    message="No runtime found",
    category=UserWarning,
)

from logging import _nameToLevel  # noqa: E402
from typing import TYPE_CHECKING  # noqa: E402

from vimseo.core.components.component_factory import ComponentFactory  # noqa: E402
from vimseo.core.pre_run_post_model import PreRunPostModel  # noqa: E402

if TYPE_CHECKING:
    from pathlib import Path

    from vimseo.core.base_integrated_model import IntegratedModel
    from vimseo.core.model_settings import IntegratedModelSettings
    from vimseo.material.material import Material
    from vimseo.material.material_registry import MaterialInfo

LOGGER = logging.getLogger(__name__)


def activate_logger(level: int | None = None):
    from gemseo import configure_logger

    if not level:
        from vimseo.config.global_configuration import _configuration as configuration

        level = _nameToLevel[configuration.logging.upper()]
    configure_logger(level=level)


def create_model(
    model_name: str,
    load_case_name: str = DUMMY_LOAD_CASE_NAME,
    model_options: IntegratedModelSettings | None = None,
    material: str | Path | Material | None = None,
    **options,
) -> IntegratedModel:
    """Create a model from its name.

    Args:
        model_name: string, name of the model to create
            (see :meth:`~vimseo.api.get_available_models` for valid names)
        load_case_name: The name of the load case that the model will execute.
        material: The material to build the model with, overriding the one its class
            declares in ``MATERIAL_FILE``. Either a material name
            (see :meth:`~vimseo.api.get_available_materials`), the path to a material
            JSON file, or a :class:`.Material`. By default, the model's own material
            is used.
        options: The options of the model.

    Returns: An instance of an :class:`.IntegratedModel`.
    """
    from vimseo.core.model_factory import ModelFactory

    if model_options:
        if options:
            msg = "Cannot specify both model_options and options"
            raise ValueError(msg)
        options.update(model_options.model_dump())
    # Passed as a constructor keyword rather than through ``IntegratedModelSettings``:
    # that settings model is ``extra="forbid"`` and is round-tripped through
    # ``model_dump()``, which would flatten a ``Material`` instance into a plain dict.
    if material is not None:
        options["material"] = material
    return ModelFactory().create(model_name, load_case_name, **options)


def get_available_materials(model_name: str = "") -> list[MaterialInfo]:
    """Find the materials a model can be built with.

    Materials are discovered across |v|'s own ``material_lib`` and that of every
    installed plugin. A material is compatible with a model when it declares the same
    ``grammar_name`` as the model's material grammar; the model's own material always
    comes first.

    Args:
        model_name: The model name. By default, every discoverable material is returned,
            regardless of any model.

    Returns:
        The compatible materials, empty if the model declares no material at all.
    """
    from vimseo.material.material_registry import available_materials
    from vimseo.material.material_registry import compatible_materials

    if not model_name:
        return available_materials()
    return compatible_materials(model_name)


def get_available_load_cases(model_name: str) -> list[str]:
    """Find the load cases available for this model.

    Args:
        model_name: The model name.

    Returns:
        The load cases associated with the specified model.
    """
    from vimseo.core.load_case_factory import LoadCaseFactory
    from vimseo.core.model_factory import ModelFactory

    lc_factory = LoadCaseFactory()
    model_class = ModelFactory().get_class(model_name)
    domain = model_class._LOAD_CASE_DOMAIN
    all_load_case_names = []
    for class_name in lc_factory.class_names:
        if domain != "" and class_name.startswith(domain):
            class_name = class_name.removeprefix(f"{domain}_")
        try:
            lc = lc_factory.create(class_name, domain=domain)
            all_load_case_names.append(lc.name)
        except ImportError:
            continue

    if model_name != "PreRunPostModel" and issubclass(model_class, PreRunPostModel):
        all_component_names = ComponentFactory().class_names
        matching_load_case_names = []
        for c in all_component_names:
            candidate_load_case_name = c.removeprefix(model_class.PRE_PROC_FAMILY + "_")
            if (
                c.startswith(model_class.PRE_PROC_FAMILY)
                and candidate_load_case_name in all_load_case_names
            ):
                matching_load_case_names.append(candidate_load_case_name)
    else:
        # TODO: for non PreRunPostModel, define the load cases used by a model explicitely (as class attribute).
        load_case_names = list(set(all_load_case_names))
        matching_load_case_names = []
        for load_case_name in load_case_names:
            if load_case_name == DUMMY_LOAD_CASE_NAME:
                continue
            try:
                create_model(
                    model_name,
                    load_case_name,
                    archive_manager="DirectoryArchive",
                )
                matching_load_case_names.append(load_case_name)
            except (ImportError, AttributeError):
                continue

    return sorted(matching_load_case_names)


def get_available_models(load_case: str = "") -> list[str]:
    """Returns the list of the available models.

    Args:
        load_case: The considered load case. If specified, only the models
            using this load case are returned.

    Returns:
        The list of names of the available models.
    """
    from vimseo.core.model_factory import ModelFactory

    mf = ModelFactory()
    model_names = mf.class_names
    if load_case == "":
        model_names.remove("PreRunPostModel")
        model_names.remove("ModelComposition")
        return model_names
    model_to_lc = {}
    for model_name in model_names:
        model_to_lc[model_name] = get_available_load_cases(model_name)
    model_names = []
    for model, load_cases in model_to_lc.items():
        if load_case in load_cases:
            model_names.append(model)

    return sorted(model_names)


def get_available_plots():
    """The available plots, deriving from ``Plotter``."""
    from vimseo.tools.post_tools.plot_factory import PlotFactory

    class_names = PlotFactory().class_names
    class_names.remove("Plotter")
    return class_names


def get_available_metrics():
    """The available comparison metrics."""
    from gemseo.utils.metrics.metric_factory import MetricFactory

    return MetricFactory().class_names


def get_available_tools():
    """The available tools."""
    from vimseo.tools.tools_factory import ToolsFactory

    class_names = ToolsFactory().class_names
    class_names.remove("BaseTool")
    return class_names


def print_config():
    """Returns: representation of the current configuration variables."""
    from vimseo.config.global_configuration import _configuration as configuration

    LOGGER.info(configuration.model_dump())


def print_config_help():
    """Return the help about configuration file."""
    from vimseo.config.global_configuration import _configuration as configuration

    LOGGER.info(configuration.model_fields)


activate_logger(_nameToLevel["INFO"])
