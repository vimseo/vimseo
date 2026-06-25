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

from vimseo.tools.base_result import BaseResult

LOGGER = logging.getLogger(__name__)


class ToolResultsFactory(BaseFactory):
    """A factory to create tool results."""

    _CLASS = BaseResult
    _PACKAGE_NAMES = ("vimseo.tools",)

    def create(
        self,
        class_name: str,
        **options,
    ) -> BaseResult:
        """Create an analysis tool.

        Args:
            name: The name of the tool result (its class name).
            **options: The options of the tool result .
        """
        return super().create(class_name, **options)
