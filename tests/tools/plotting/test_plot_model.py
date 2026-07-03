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

# Copyright (c) 2024 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - initial API and implementation and/or
#    initial documentation
#        :author: Benedicte REINE
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
from __future__ import annotations

from pathlib import Path

import pytest

from vimseo.api import create_model


@pytest.mark.parametrize(
    ("model", "load_case"),
    [
        ("BendingTestAnalytical", "Cantilever"),
        ("MockModel", "LC2"),
    ],
)
def test_plot_model(tmp_wd, model, load_case):
    """Check that the curves of a model are correctly plotted."""
    model = create_model(model, load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute()
    model.plot_results()
    expected_curves = model.CURVES + model.load_case.plot_parameters.curves

    assert model.curves == expected_curves

    for variables in expected_curves:
        assert Path(
            model.archive_manager.job_directory
            / f"{model.name}_{load_case}_{variables[1]}_vs_{variables[0]}.html"
        ).is_file()
