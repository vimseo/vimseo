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

from numpy import array
from numpy.testing import assert_array_equal


def check_distribution(parameter_space, var_name, parameters=(), **kwargs):
    """Check distribution name and min and max values."""

    if len(parameters) > 0:
        if len(parameter_space.distributions[var_name].marginals) == 1:
            parameters_from_distribution = (
                parameter_space.distributions[var_name].marginals[0].settings
            )
            assert parameters == parameters_from_distribution["parameters"]
        else:
            msg = "Unhandled case for interfaces distribution of a vector."
            raise ValueError(msg)
    else:
        if "name" in kwargs and kwargs["name"] == "Weibull":
            kwargs["name"] = "WeibullMin"
        for k, v in kwargs.items():
            print("Parameter name: ", k)
            print("Expected value: ", v)
            parameters_from_distribution = [
                parameter_space.distributions[var_name].marginals[i].settings[k]
                for i in range(len(parameter_space.distributions[var_name].marginals))
            ]
            print(
                "Value from parameter space distribution: ",
                parameters_from_distribution,
            )
            assert_array_equal(array(v), array(parameters_from_distribution))
