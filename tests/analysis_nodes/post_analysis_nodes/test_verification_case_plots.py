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

"""Tests of the plots of the solution verification cases."""

from __future__ import annotations

import pytest
from numpy.testing import assert_allclose
from pandas import DataFrame

from vimseo.analysis_nodes.post_analysis_nodes.verification_case_plots import (
    ConvergenceCase,
)


@pytest.fixture
def convergence_data() -> DataFrame:
    """Two convergence trajectories of two meshes each."""
    return DataFrame({
        "element_size": [2.0, 1.0, 2.0, 1.0],
        "y": [4.0, 2.0, 8.0, 4.0],
        "Ref[y]": [1.0, 1.0, 2.0, 2.0],
        "extrapolated_values_folds": [1.0, 1.0, 2.0, 2.0],
    })


@pytest.mark.parametrize(
    ("normalize_index_output", "y_title", "divisors"),
    [(None, "<b>y</b>", (1.0, 1.0)), (0, "<b>Normalized y</b>", (4.0, 8.0))],
)
def test_convergence_case(
    tmp_wd, convergence_data, normalize_index_output, y_title, divisors
):
    """Check the axis titles, and that the reference lines are normalized like the
    trajectories, including by the first mesh (#42)."""
    plot = ConvergenceCase()
    plot.execute(
        convergence_data,
        2,
        "element_size",
        "y",
        normalize_index_output=normalize_index_output,
        save=False,
    )
    figure = plot.result.figure

    assert figure.layout.xaxis.title.text == "<b>element_size</b>"
    assert figure.layout.yaxis.title.text == y_title
    reference_lines = [
        trace
        for trace in figure.data
        if trace.mode == "lines" and trace.line.dash == "dash"
    ]
    assert len(reference_lines) == 2
    for line, (reference, last), divisor in zip(
        reference_lines, ((1.0, 2.0), (2.0, 4.0)), divisors, strict=True
    ):
        assert_allclose(line.y, (reference / divisor, last / divisor))
