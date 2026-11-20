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
from typing import Any

from gemseo.core.base_factory import BaseFactory

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.factory import create_instance
from vimseo.core.factory import get_class

LOGGER = logging.getLogger(__name__)


class ModelFactory(BaseFactory):
    """Model factory to create the Model from a name or a class."""

    _CLASS = IntegratedModel
    _PACKAGE_NAMES = ("vimseo.problems",)

    def create(self, class_name: str, *args: Any, **kwargs: Any) -> IntegratedModel:
        """Return an instance of a model.

        Args:
            class_name: The name of the model.
            *args: The positional arguments of the constructor of the model,
                e.g. the name of the load case.
            **kwargs: The keyword arguments of the constructor of the model.

        Returns:
            The model.

        Raises:
            ImportError: If the model is not available.
            TypeError: If the model cannot be created, e.g. because its constructor
                does not accept the arguments.
        """
        cls = get_class(
            self,
            class_name,
            "model",
            "A model must be a subclass of IntegratedModel defined in a module of "
            "vimseo.problems or of a plugin declared by a gemseo_plugins entry point.",
            self.class_names,
        )
        return create_instance(
            cls,
            "model",
            "``def __init__(self, load_case_name: str, **options)`` calling "
            "``super().__init__(load_case_name, **options)``",
            *args,
            **kwargs,
        )

    @property
    def class_names(self) -> list[str]:
        """The sorted names of the available classes."""
        class_names = sorted(self._names_to_class_info.keys())
        class_names.remove("IntegratedModel")
        class_names.remove("BaseDisciplineModel")
        return class_names
