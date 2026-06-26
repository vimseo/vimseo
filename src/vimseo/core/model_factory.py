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

    @property
    def class_names(self) -> list[str]:
        """The sorted names of the available classes."""
        class_names = sorted(self._names_to_class_info.keys())
        class_names.remove("IntegratedModel")
        class_names.remove("BaseDisciplineModel")
        return class_names
