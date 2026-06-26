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

"""A material relation.

The use ontology is based on
https://emmo-repo.github.io/versions/1.0.0-beta/emmo.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from vimseo.material.metadata import MaterialMetadata
from vimseo.utilities.json_grammar_utils import BaseJsonIO

if TYPE_CHECKING:
    from vimseo.material.material_property import MaterialProperty


class MaterialRelation(BaseJsonIO):
    """A material relation."""

    tag: str = ""
    name: str
    metadata: MaterialMetadata = Field(default_factory=lambda: MaterialMetadata())
    properties: list[MaterialProperty]

    def get_values_as_dict(self):
        return {prop.name: prop.value for prop in self.properties}

    def get_card(self) -> str:
        """Return a card for a mechanical solver."""
        return ""
