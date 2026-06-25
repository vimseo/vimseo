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

import numpy as np
import pytest
from scipy.interpolate import interp1d

from vimseo.api import create_model


@pytest.mark.fast
@pytest.mark.parametrize(
    "input_data",
    [
        ({}),
        ({
            "length": np.array([500.0]),
            "width": np.array([35.0]),
            "height": np.array([20.0]),
            "imposed_dplt": np.array([-10]),
            "relative_dplt_location": np.array([0.8]),
        }),
    ],
)
def test_cantilever(tmp_wd, input_data):
    """Check that the BendingTestAnalytical Cantilever model results obtained by
    integration correlate the literal expression."""
    model = create_model("BendingTestAnalytical", "Cantilever")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute(input_data)

    reaction_forces = model.get_output_data()["reaction_forces"][0]
    max_dplt = model.get_output_data()["maximum_dplt"][0]
    location_max_dplt = model.get_output_data()["location_max_dplt"][0]

    imposed_dplt = model.get_input_data()["imposed_dplt"][0]
    young_modulus = model.get_input_data()["young_modulus"][0]
    quadratic_moment = model._pre_processor.get_output_data()["quadratic_moment"][0]

    imposed_dplt_location = (
        model._pre_processor.get_output_data()["imposed_dplt_location"]
    )[0]
    length = model.get_input_data()["length"][0]
    expected_reaction_forces = (
        3 * imposed_dplt * young_modulus * quadratic_moment / imposed_dplt_location**3
    )
    expected_max_dplt = (
        expected_reaction_forces
        * imposed_dplt_location**2
        * (3 * length - imposed_dplt_location)
        / (6 * young_modulus * quadratic_moment)
    )
    assert max_dplt == pytest.approx(expected_max_dplt, rel=1e-3)
    assert reaction_forces == pytest.approx(expected_reaction_forces, rel=1e-3)
    assert location_max_dplt == pytest.approx(length, rel=1e-2)


@pytest.mark.fast
@pytest.mark.parametrize(
    "input_data",
    [
        ({}),
        ({
            "length": np.array([500.0]),
            "width": np.array([35.0]),
            "height": np.array([20.0]),
            "imposed_dplt": np.array([-10.0]),
            "relative_support_location": np.array([0.2]),
        }),
    ],
)
def test_three_points(tmp_wd, input_data):
    """
    Check that the three point bending model results obtained by integration correlate the
    literal expression.
    Args:
        input_data: input data

    Returns:

    """
    model = create_model("BendingTestAnalytical", "ThreePoints")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute(input_data)

    reaction_forces = model.get_output_data()["reaction_forces"][0]
    max_dplt = model.get_output_data()["maximum_dplt"][0]
    location_max_dplt = model.get_output_data()["location_max_dplt"][0]

    imposed_dplt = model.get_input_data()["imposed_dplt"][0]
    young_modulus = model.get_input_data()["young_modulus"][0]
    quadratic_moment = model._pre_processor.get_output_data()["quadratic_moment"][0]
    imposed_dplt_location = (
        model._pre_processor.get_output_data()["imposed_dplt_location"]
    )[0]
    support_location = model._pre_processor.get_output_data()["support_location"]
    support_length = support_location[1] - support_location[0]
    a = imposed_dplt_location - support_location[0]
    b = support_location[1] - imposed_dplt_location

    expected_reaction_forces = (
        3
        * imposed_dplt
        * young_modulus
        * quadratic_moment
        * support_length
        / (a**2 * b**2)
    )
    expected_max_dplt = (
        expected_reaction_forces
        * min(a, b)
        / (27 * young_modulus * quadratic_moment * support_length)
    ) * np.sqrt(3 * (support_length**2 - min(a, b) ** 2) ** 3)
    if a < b:
        expected_loc_max_dplt = (
            (support_length / 2)
            * (1 + (1 - np.sqrt((4 / 3) * (1 - min(a, b) ** 2 / support_length**2))))
        ) + support_location[0]
    else:
        expected_loc_max_dplt = (
            (support_length / 2)
            * (1 - (1 - np.sqrt((4 / 3) * (1 - min(a, b) ** 2 / support_length**2))))
        ) + support_location[0]

    assert max_dplt == pytest.approx(expected_max_dplt, rel=0.5)
    assert reaction_forces == pytest.approx(expected_reaction_forces)
    # TODO check why need such high tolerance.
    assert location_max_dplt == pytest.approx(expected_loc_max_dplt, rel=5e-2)


# TODO: could be relevant to specify all (or most of) the input parameters in a rather
# simple configuration (in particular for ThreePoints load case)
@pytest.mark.parametrize(
    ("load_case", "relative_dplt_location", "max_moment_index"),
    [
        ("Cantilever", 0.1, 0),
        ("Cantilever", 1.0, 0),
        ("ThreePoints", None, 1),
    ],
)
def test_moment(tmp_wd, load_case, relative_dplt_location, max_moment_index):
    """
    Check the value of the moment.
    Compare the internal and external energies.
    Args:
        load_case : the loadcase
        max_moment_index: index of the maximum of moment.

    Returns:

    """
    model = create_model("BendingTestAnalytical", load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    input_data = {
        "height": np.array([20.0]),
    }
    if relative_dplt_location is not None:
        input_data.update({
            "relative_dplt_location": np.array([relative_dplt_location])
        })

    model.execute(input_data)
    out = model.get_output_data()

    assert np.argmax(abs(out["moment"])) == max_moment_index

    reaction_forces = out["reaction_forces"][0]
    moment_grid = out["moment_grid"]
    moment = out["moment"]
    disp = model.get_input_data()["imposed_dplt"]

    # compare energies
    from scipy.integrate import quad

    w_external = 0.5 * reaction_forces * disp

    w_internal = quad(
        fun_squared_moment,
        a=moment_grid[0],
        b=moment_grid[-1],
        args=(moment_grid, moment),
    ) / (
        model.get_input_data()["young_modulus"][0]
        * model._pre_processor.get_output_data()["quadratic_moment"][0]
    )

    assert w_external[0] == pytest.approx(w_internal[0] * 0.5, rel=1e-2)


def fun_squared_moment(x, moment_grid, moment):
    m_func = interp1d(moment_grid, moment)
    return m_func(x) ** 2


@pytest.mark.parametrize(
    ("load_case", "height"),
    [
        ("ThreePoints", 15.0),
        ("ThreePoints", 20.0),
        ("Cantilever", 15.0),
        ("Cantilever", 20.0),
    ],
)
def test_displacement_profile(tmp_wd, load_case, height):
    """
    Check that the double derivative of the displacement is equal to the moment divided
    by the product of Young's modulus times the quadratic moment.
    Args:
        load_case: the load case
        height: the height of the beam

    Returns:

    """
    model = create_model("BendingTestAnalytical", load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute({"height": np.array([height])})

    young_modulus = model.get_input_data()["young_modulus"][0]
    quadratic_moment = (
        model.get_input_data()["width"][0]
        * model.get_input_data()["height"][0] ** 3
        / 12
    )

    out = model.get_output_data()
    x = out["dplt_grid"]
    y_prime = np.diff(out["dplt"]) / np.diff(x)
    y_second = np.diff(y_prime) / np.diff(x[:-1])
    y_second_expected = -model.run.m_func(x[1:-1]) / (young_modulus * quadratic_moment)
    assert y_second == pytest.approx(y_second_expected, rel=1e-5)
