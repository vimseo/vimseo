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

from vimseo.core.components.external_software_component import BaseComponent

LOGGER = logging.getLogger(__name__)


class ComponentFactory(BaseFactory):
    """BaseComponent factory to create a component from a name or a class."""

    _CLASS = BaseComponent
    _PACKAGE_NAMES = (
        "vimseo.problems",
        "vimseo.core.components.pre",
        "vimseo.core.components.run",
        "vimseo.core.components.post",
        "vimseo.core.components.subroutines",
    )

    SEP = "_"
    """The character used to separate the BaseComponent name from the loadcase."""

    def create(
        self,
        base_class_name: str,
        load_case_name: str = "",
        **options: Any,
    ) -> Any:
        """Return an instance of a class.

        Args:
            base_class_name: The name of the family class of component to create.
            load_case_name: The name of the load case.
            **options: The arguments to be passed to the class constructor.

        Returns:
            The instance of the class.

        Raises:
            TypeError: If the class cannot be instantiated.
        """

        if base_class_name is None:
            return None

        if load_case_name == "":
            class_name = base_class_name
        else:
            class_name = base_class_name + self.SEP + load_case_name

        try:
            klass = self.get_class(class_name)
            return klass(load_case_name=load_case_name, **options)
        except TypeError:
            LOGGER.exception(
                "Failed to create class %s with arguments %s %s",
                base_class_name,
                load_case_name,
                options,
            )
