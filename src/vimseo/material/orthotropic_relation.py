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

# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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

from composipy import OrthotropicMaterial

from vimseo.material.material_property import MaterialProperty
from vimseo.material.material_relation import MaterialRelation


class OrthotropicRelation(MaterialRelation):
    """A class representing the properties of an orthotropic material."""

    name: str = "orthotropic"
    thickness: float = 1.0

    def get_relation(self) -> OrthotropicMaterial:
        """Return the type of the material relation."""
        properties = self.get_values_as_dict()
        return OrthotropicMaterial(
            e1=properties["E1"],
            e2=properties["E2"],
            g12=properties["G12"],
            v12=properties["nu12"],
            thickness=self.thickness,
            t1=properties["Xt"],
            c1=properties["Xc"],
            t2=properties["Yt"],
            c2=properties["Yc"],
            s=properties["S12"],
        )

    def model_post_init(self, __context):
        """Post-initialization checks."""
        self.properties = [
            MaterialProperty(name="E1", value=0.0),
            MaterialProperty(name="E2", value=0.0),
            MaterialProperty(name="G12", value=0.0),
            MaterialProperty(name="nu12", value=0.0),
            MaterialProperty(name="Xt", value=0.0),
            MaterialProperty(name="Xc", value=0.0),
            MaterialProperty(name="Yt", value=0.0),
            MaterialProperty(name="Yc", value=0.0),
            MaterialProperty(name="S12", value=0.0),
        ]

    def set_thickness(self, thickness: float) -> None:
        """Set the thickness of the material."""
        self.thickness = thickness
