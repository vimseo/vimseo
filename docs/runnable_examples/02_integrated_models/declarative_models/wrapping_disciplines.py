# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This work is licensed under a BSD 0-Clause License.
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
# FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""GEMSEO disciplines wrapped as VIMSEO models by the YAML files of this directory.

- ``Rectangle``: a ``SimpleGrammar``, giving the types of the inputs only.
- ``CantileverBeam``: a ``JSONGrammar`` built from data, so without bounds.
- ``BoundedCantileverBeam``: a ``JSONGrammar`` read from a file with bounds.
"""

from __future__ import annotations

from pathlib import Path

from gemseo.core.discipline import Discipline
from numpy import atleast_1d
from numpy import linspace
from numpy import ndarray

HERE = Path(__file__).parent


class Rectangle(Discipline):
    """The area and the perimeter of a rectangle, with a SimpleGrammar."""

    default_grammar_type = Discipline.GrammarType.SIMPLE

    def __init__(self) -> None:
        super().__init__()
        self.input_grammar.update_from_types({"width": ndarray, "height": ndarray})
        self.output_grammar.update_from_types({"area": ndarray, "perimeter": ndarray})
        self.default_input_data = {
            "width": atleast_1d(2.0),
            "height": atleast_1d(3.0),
        }

    def _run(self, input_data):
        width = input_data["width"]
        height = input_data["height"]
        return {"area": width * height, "perimeter": 2 * (width + height)}


class CantileverBeam(Discipline):
    """A cantilever beam with a tip load, with a JSONGrammar without bounds.

    The grammar is built from the default values: only the types are known.
    """

    def __init__(self, n_points: int = 20) -> None:
        """
        Args:
            n_points: The number of points of the deflection curve.
        """
        super().__init__()
        self._n_points = n_points
        default_input_data = {
            "length": atleast_1d(1000.0),  # mm
            "width": atleast_1d(50.0),  # mm
            "height": atleast_1d(100.0),  # mm
            "young_modulus": atleast_1d(210000.0),  # MPa
            "force": atleast_1d(1000.0),  # N
        }
        self.input_grammar.update_from_data(default_input_data)
        self.default_input_data = default_input_data
        self.output_grammar.update_from_data({
            "tip_deflection": atleast_1d(0.0),
            "max_stress": atleast_1d(0.0),
            "x": linspace(0.0, 1.0, n_points),
            "deflection": linspace(0.0, 1.0, n_points),
        })

    def _run(self, input_data):
        length = input_data["length"][0]
        width = input_data["width"][0]
        height = input_data["height"][0]
        young_modulus = input_data["young_modulus"][0]
        force = input_data["force"][0]
        inertia = width * height**3 / 12
        x = linspace(0.0, length, self._n_points)
        deflection = force * x**2 * (3 * length - x) / (6 * young_modulus * inertia)
        return {
            "tip_deflection": atleast_1d(deflection[-1]),
            "max_stress": atleast_1d(force * length * height / 2 / inertia),
            "x": x,
            "deflection": deflection,
        }


class BoundedCantileverBeam(CantileverBeam):
    """The same beam, whose input grammar is read from a JSON file with bounds."""

    def __init__(self, n_points: int = 20) -> None:
        super().__init__(n_points)
        # The properties of the file replace those built from the default values.
        self.input_grammar.update_from_file(HERE / "BoundedCantileverBeam_input.json")
