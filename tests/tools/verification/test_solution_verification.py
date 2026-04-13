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
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import array
from numpy import atleast_1d
from numpy import empty
from numpy import ones
from numpy.testing import assert_allclose
from numpy.testing import assert_array_equal
from pandas import DataFrame

from vimseo.api import create_model
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.verification.solution_verification import Analysis
from vimseo.tools.verification.solution_verification import (
    DiscretizationSolutionVerification,
)
from vimseo.tools.verification.verification_result import SolutionVerificationResult

ELEMENT_SIZES = [0.45, 0.25, 0.15, 0.1]
ELEMENT_SIZE_RATIO = 1.2


@pytest.fixture
def convergence_verificator():
    """A convergence verificator."""
    model = create_model("MockConvergence", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    verificator = DiscretizationSolutionVerification(
        directory_naming_method=DirectoryNamingMethod.NUMBERED,
    )
    verificator.execute(
        model=model,
        element_size_variable_name="h",
        element_size_values=ELEMENT_SIZES,
        output_name="a_h",
    )
    return verificator


def test_convergence(tmp_wd, convergence_verificator):
    """Check code convergence verification tool."""
    model = create_model("MockConvergence", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    result = convergence_verificator.result

    for cross_validation_folds in result.cross_validation.values():
        assert cross_validation_folds["beta"] == pytest.approx(2.0)
        assert cross_validation_folds["q_extrap"] == pytest.approx(1.0)
        assert len(cross_validation_folds["h"]) == 3
        assert set(cross_validation_folds["h"]).issubset(set(ELEMENT_SIZES))

    assert result.extrapolation["beta"] == pytest.approx(2.0)
    assert result.extrapolation["beta_mad"] == pytest.approx(0.0)
    assert result.extrapolation["q_extrap"] == pytest.approx(1.0)
    assert result.extrapolation["q_extrap_mad"] == pytest.approx(0.0)
    q = (
        convergence_verificator.result.simulation_and_reference
        .get_view(variable_names="a_h")
        .to_numpy()
        .ravel()
    )
    h = (
        convergence_verificator.result.simulation_and_reference
        .get_view(variable_names="h")
        .to_numpy()
        .ravel()
    )
    assert (h == ELEMENT_SIZES).all()

    gci_fine = 1.25 * (q[3] - q[2]) / q[3] * 1.0 / ((h[2] / h[3]) ** 2 - 1)
    gci_coarse = 1.25 * (q[1] - q[0]) / q[1] * 1.0 / ((h[0] / h[1]) ** 2 - 1)
    assert_allclose(result.extrapolation["gci"], array([gci_coarse, gci_fine]))

    error = (
        result.element_wise_metrics.get_view(variable_names="a_h").to_numpy().ravel()
    )
    expected_error = empty(4)
    for i, h in enumerate(ELEMENT_SIZES):
        model.execute({"h": atleast_1d(h)})
        expected_error[i] = (
            model.get_input_data()["a"][0] - model.get_output_data()["a_h"][0]
        )
    assert_allclose(expected_error, error)


def test_convergence_versus_n_dof(tmp_wd):
    """Check code convergence for an N_DOF analysis."""
    model = create_model("MockConvergence", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    verificator = DiscretizationSolutionVerification(
        directory_naming_method=DirectoryNamingMethod.NUMBERED,
    )
    verificator.execute(
        model=model,
        element_size_variable_name="h",
        element_size_values=ELEMENT_SIZES,
        output_name="a_h",
        analysis=Analysis.N_DOF,
        abscissa_name="n_dof",
    )
    result = verificator.result
    assert (
        DiscretizationSolutionVerification._DOF_ABSCISSA_NAME
        in result.element_wise_metrics.get_variable_names(
            group_name=IODataset.INPUT_GROUP
        )
    )
    assert result.element_wise_metrics.get_view(
        variable_names=DiscretizationSolutionVerification._DOF_ABSCISSA_NAME
    ).to_numpy().ravel()[0] == pytest.approx(1)


def test_plot(tmp_wd, convergence_verificator):
    """Check that the convergence verification plot are written on disk."""
    convergence_verificator.plot_results(
        convergence_verificator.result,
        directory_path=Path.cwd(),
        save=True,
        show=False,
    )
    assert Path("convergence_a_h_versus_h.html").is_file()
    assert Path("a_h_error_versus_h.html").is_file()
    assert Path("a_h_error_versus_cpu_time.html").is_file()
    assert Path("a_h_error_versus_element_size.html").is_file()


def test_repr(tmp_wd, convergence_verificator):
    """Check representation of the convergence verification result."""
    expected_words = [
        "Richardson extrapolation:",
        "Cross validation on Richardson extrapolation:",
    ]
    for word in expected_words:
        assert word in str(convergence_verificator.result)


def test_verification_from_ratio(tmp_wd):
    """A convergence verificator based on a ratio of mesh size."""
    model = create_model("MockConvergence", "Dummy")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    verificator = DiscretizationSolutionVerification(
        directory_naming_method=DirectoryNamingMethod.NUMBERED,
    )
    verificator.execute(
        model=model,
        element_size_variable_name="h",
        element_size_ratio=ELEMENT_SIZE_RATIO,
        output_name="a_h",
    )
    h = (
        verificator.result.simulation_and_reference
        .get_view(variable_names="h")
        .to_numpy()
        .ravel()
    )
    dx_0 = model.default_input_data["h"][0]
    assert_array_equal(
        h,
        array([
            dx_0 * ELEMENT_SIZE_RATIO,
            dx_0,
            dx_0 * ELEMENT_SIZE_RATIO ** (-1),
            dx_0 * ELEMENT_SIZE_RATIO ** (-2),
        ]),
    )


def test_from_data(tmp_wd):
    """Check that solution verification can take simulated data."""

    df = DataFrame.from_dict({
        ("inputs", "h", 0): array([0.5, 0.4, 0.3, 0.2, 0.1]),
        ("outputs", "a_h", 0): array([1.5, 1.4, 1.3, 1.2, 1.1]),
        ("outputs", "y1", 0): ones(5),
        ("outputs", "y2", 0): ones(5),
    })
    verificator = DiscretizationSolutionVerification(
        directory_naming_method=DirectoryNamingMethod.NUMBERED,
    )
    verificator.execute(
        element_size_variable_name="h",
        output_name="a_h",
        simulated_data=df,
        observed_output_names=["y1"],
    )
    verificator.plot_results(verificator.result, save=True, show=False)


def test_serialization(tmp_wd, convergence_verificator):
    """Check that a SolutionVerificationResult can be serialized to hdf5."""
    result = convergence_verificator.result
    result.to_hdf5("result.hdf5")
    serialized_result = SolutionVerificationResult.from_hdf5("result.hdf5")
    assert_results_equal(result, serialized_result)
