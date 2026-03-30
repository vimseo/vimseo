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


import pytest
from numpy.testing import assert_array_almost_equal

from vimseo.api import create_model
from vimseo.core.model_result import ModelResult
from vimseo.problems.tan_oh.tan_oht import NOMINAL_GRID_SIZE


def test_tan_oh_default_inputs(tmp_wd):
    """Check that OHT Tan model runs with default inputs."""
    model = create_model("TanOpenHole", "OHT")
    output_data = model.execute()
    input_data = model.get_input_data()
    model_result = ModelResult.from_data(
        {"outputs": output_data, "inputs": input_data}, load_fields=True
    )

    for n_name, sigma_name in zip(
        ["N_xx", "N_yy", "N_xy"], ["sigma_xx", "sigma_yy", "sigma_xy"], strict=False
    ):
        n_data = model_result.fields["flux"][0].point_data[n_name]
        sigma_data = model_result.fields["flux"][0].point_data[sigma_name]
        assert n_data.shape == ((NOMINAL_GRID_SIZE * NOMINAL_GRID_SIZE),)
        assert_array_almost_equal(n_data, sigma_data / input_data["thickness"][0])

    assert output_data["sigma_xx_d0"] == pytest.approx(10490.0, rel=1e-2)

    assert (model.archive_manager.job_directory / "flux.vtk").exists()
