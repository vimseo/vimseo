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

from gemseo.core.base_factory import BaseFactory

from vimseo.core.base_integrated_model import IntegratedModel

LOGGER = logging.getLogger(__name__)


class ModelFactory(BaseFactory):
    """Model factory to create the Model from a name or a class."""

    _CLASS = IntegratedModel
    _PACKAGE_NAMES = ("vimseo.problems",)

    def update(self) -> None:
        """Search for the model classes, warning about the declared models named like
        another model."""
        super().update()
        self.__warn_about_declared_name_clashes()

    def __warn_about_declared_name_clashes(self) -> None:
        """Log a warning for each declared model named like another model.

        The model factory keeps a single class per name, so ``create_model`` would
        create one of them depending on the import order.
        """
        from vimseo.core.declarative_model import REGISTRY_MODULE_NAME

        class_infos = self._names_to_class_info
        library_names = {info.library_name for info in class_infos.values()}
        names_to_modules = {}
        classes = [IntegratedModel]
        while classes:
            cls = classes.pop()
            classes.extend(cls.__subclasses__())
            if cls.__module__.split(".")[0] in library_names:
                names_to_modules.setdefault(cls.__name__, set()).add(cls.__module__)
        for name, module_names in sorted(names_to_modules.items()):
            if (
                REGISTRY_MODULE_NAME in module_names
                and len(module_names) > 1
                and name in class_infos
            ):
                LOGGER.warning(
                    "The declared model %s has the name of a model of %s; "
                    "create_model creates the one of %s: rename the declared model.",
                    name,
                    ", ".join(sorted(module_names - {REGISTRY_MODULE_NAME})),
                    class_infos[name].class_.__module__,
                )

    @property
    def class_names(self) -> list[str]:
        """The sorted names of the available classes."""
        class_names = sorted(self._names_to_class_info.keys())
        class_names.remove("IntegratedModel")
        class_names.remove("BaseDisciplineModel")
        return class_names
