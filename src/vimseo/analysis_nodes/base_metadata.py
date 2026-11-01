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

"""A base metadata."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from docstring_inheritance import GoogleDocstringInheritanceMeta

import vimseo


@dataclass
class BaseMetadata(metaclass=GoogleDocstringInheritanceMeta):
    """A base metadata."""

    generic: dict = field(default_factory=dict)
    """Generic metadata like data, time and |v| version."""

    misc: dict = field(default_factory=dict)
    """Miscellaneous."""

    def __post_init__(self):
        self.generic = {
            "datetime": datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
            "version": vimseo.__version__,
        }
