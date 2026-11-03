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
from vimseo.core.factory import create_instance
from vimseo.core.factory import get_class

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
        **options: Any,
    ) -> Any:
        """Return an instance of a class.

        Args:
            base_class_name: The name of the family class of component to create.
            **options: The arguments to be passed to the class constructor.

        Returns:
            The instance of the class.

        Raises:
            ImportError: If the class is not available.
            TypeError: If the constructor of the class does not accept the options.
        """

        if base_class_name is None:
            return None

        if "load_case" not in options:
            class_name = base_class_name
            hint = "A component must be a subclass of BaseComponent."
            available_names = None
        else:
            load_case_name = options["load_case"].name
            class_name = base_class_name + self.SEP + load_case_name
            hint = (
                f"The component of family {base_class_name} for the load case "
                f"{load_case_name} must be a subclass of BaseComponent named "
                f"{class_name}, i.e. {{Family}}{self.SEP}{{LoadCase}}."
            )
            available_names = [
                name
                for name in self.class_names
                if name.startswith(base_class_name + self.SEP)
            ]

        klass = get_class(self, class_name, "component", hint, available_names)
        return create_instance(
            klass,
            "component",
            "``def __init__(self, load_case: LoadCase | None = None, **options)`` "
            "calling ``super().__init__(load_case=load_case, **options)``",
            **options,
        )
