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

"""Handling of model default inputs by splitting the input variables by category."""

from __future__ import annotations

from typing import TYPE_CHECKING

from numpy import atleast_1d

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from numbers import Number

    from vimseo.core.base_integrated_model import IntegratedModel


class InputDataHandler:
    """A handler on model default inputs to ease get/set access to model default
    inputs."""

    def __init__(self, model: IntegratedModel):
        self.__model = model

    def set_data(self, data: Mapping[str, Number | str]):
        """Set the model default inputs."""
        self.__model.default_input_data.update({
            name: atleast_1d(value) for name, value in data.items()
        })

    def get_data(self, names: Iterable[str]):
        """Return a dictionary containing the values corresponding to the names.

        The values are numbers or strings. Only default inputs being arrays of size equal
        to one are retained.
        """
        return {
            name: (
                self.__model.default_input_data[name][0]
                if self.__model.default_input_data[name].size == 1
                else self.__model.default_input_data[name]
            )
            for name in names
        }

    def get_material_data(self):
        """Get the material default data of the model."""
        return self.get_data(self.__model.material_variable_names)

    def get_numerical_data(self):
        """Get the numerical default data of the model."""
        return self.get_data(self.__model.numerical_variable_names)

    def get_geometrical_data(self):
        """Get the geometrical default data of the model."""
        return self.get_data(self.__model.geometrical_variable_names)

    def get_boundary_condition_data(self):
        """Get the boundary conditions default data of the model."""
        return self.get_data(self.__model.boundary_condition_variable_names)
