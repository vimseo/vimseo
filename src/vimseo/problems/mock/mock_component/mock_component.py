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

from __future__ import annotations

from numpy import array
from numpy import atleast_1d

from vimseo.core.components.base_component import BaseComponent


class MockComponent(BaseComponent):
    """Default component."""

    def _run(self, input_data):
        y1 = array([0.1])
        y2 = array([0.2])
        y3 = array([0.3])

        self.io.update_output_data({"y1": y1, "y2": y2, "y3": y3})


class MockComponent2(MockComponent):
    """Default component with no input_grammar/output_grammar files in .json."""


class MockComponent3(MockComponent):
    """Default component with no input_grammar files in .json."""


class MockComponent4(MockComponent):
    """Default component with no output_grammar files in .json."""


class MockChildComponent1(MockComponent2):
    """Default Mock component child."""

    def __init__(self, **options):
        super().__init__(**options)
        self.default_input_data.update({
            "x1": atleast_1d(0.0),
            "x2": atleast_1d(0.0),
            "x3": atleast_1d(0.0),
        })
