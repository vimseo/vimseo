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

from pathlib import Path

import pytest
from numpy.testing import assert_allclose

from vimseo.tools.io.field_result import FieldResult
from vimseo.tools.io.reader_file_tecplot import ReaderFileTecplot

# A single-quad FEBLOCK zone, mimicking a CFD surface export whose coordinate
# variables are not named X/Y/Z, as meshio's Tecplot reader requires.
_TECPLOT_CONTENT = """\
TITLE = "single quad"
VARIABLES = "CoordinateX" "CoordinateY" "CoordinateZ" "Pressure"
ZONE T="patch", N=4, E=1, ET=QUADRILATERAL, F=FEBLOCK
0.0 1.0 1.0 0.0
0.0 0.0 1.0 1.0
0.0 0.0 0.0 0.0
10.0 20.0 30.0 40.0
1 2 3 4
"""


def test_reader_file_tecplot(tmp_wd):
    file_name = "surface.dat"
    Path(file_name).write_text(_TECPLOT_CONTENT)

    reader = ReaderFileTecplot()
    result = reader.execute(
        file_name=file_name,
        variable_name_aliases={
            "CoordinateX": "X",
            "CoordinateY": "Y",
            "CoordinateZ": "Z",
        },
    )

    assert isinstance(result, FieldResult)
    field = result.field
    assert field.mesh_points.shape == (4, 3)
    assert_allclose(field.mesh_points[:, 0], [0.0, 1.0, 1.0, 0.0])
    assert len(field.mesh_cells) == 1
    assert field.mesh_cells[0].type == "quad"
    assert field.mesh_cells[0].data.shape == (1, 4)
    assert field.point_variable_names == ["Pressure"]
    assert_allclose(field.point_data["Pressure"], [10.0, 20.0, 30.0, 40.0])


def test_reader_file_tecplot_wrong_extension(tmp_wd):
    file_name = "surface.txt"
    Path(file_name).write_text(_TECPLOT_CONTENT)

    reader = ReaderFileTecplot()
    with pytest.raises(ValueError, match="requires the file suffix to be .dat"):
        reader.execute(file_name=file_name)
