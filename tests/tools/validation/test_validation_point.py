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

import pytest
from gemseo import create_discipline
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from numpy import atleast_1d
from numpy.testing import assert_array_equal

from vimseo.api import create_model
from vimseo.tools.post_tools.distribution_comparison_plot import DistributionComparison
from vimseo.tools.space.random_variable_interface import add_random_variable_interface
from vimseo.tools.validation.test_data import VALIDATION_DATA_DIR
from vimseo.tools.validation.validation_point import StochasticValidationPoint
from vimseo.tools.validation.validation_point import read_nominal_values
from vimseo.utilities.datasets import DatasetAddFromModel
from vimseo.utilities.datasets import DatasetAddFromStatistics
from vimseo.utilities.distribution import DistributionParameters


@pytest.fixture
def validation_point():
    bias = 0.1
    distribution_name = "Uniform"
    metric_names = []

    nb_samples = 10
    model_expression = {"y1": "(x1 + x1_2 + 2) * 2 + 1"}

    measured_data = Dataset()
    uncertain_variable_distributions = {
        "x1_2": DistributionParameters(
            name="Triangular", lower=0.0, upper=0.9, mode=0.5
        ),
    }
    uncertain_input_space = ParameterSpace()
    for name, distribution in uncertain_variable_distributions.items():
        add_random_variable_interface(uncertain_input_space, name, distribution)

    nominal_data = {"x1": 0.5, "x1_2": 0.5}
    dataset_manipulator = DatasetAddFromStatistics()
    dataset_manipulator.add_group(
        measured_data,
        IODataset.INPUT_GROUP,
        ["x1"],
        {"x1": DistributionParameters(name=distribution_name, lower=0.0, upper=0.9)},
        nb_samples,
    )
    model_for_sample_generation = create_discipline(
        "AnalyticDiscipline", expressions=model_expression
    )
    model_for_sample_generation.default_input_data["x1_2"] = atleast_1d(
        uncertain_variable_distributions["x1_2"].model_dump()["mode"]
    )
    DatasetAddFromModel.add_group(
        measured_data,
        IODataset.INPUT_GROUP,
        ["x1"],
        model_for_sample_generation,
        IODataset.OUTPUT_GROUP,
        "y1",
        bias=bias,
    )

    model = create_model("MockModel", "LC2")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    validation_point_tool = StochasticValidationPoint()
    validation_point_tool.execute(
        inputs=validation_point_tool._INPUTS(
            model=model,
            measured_data=measured_data,
            uncertain_input_space=uncertain_input_space,
        ),
        settings=validation_point_tool._SETTINGS(
            metric_names=metric_names,
            n_samples=nb_samples,
            tested_distributions=["Uniform", "Normal"],
            nominal_data=nominal_data,
        ),
    )
    return validation_point_tool, model, nominal_data


# TODO add test with model bound truncation
@pytest.mark.parametrize("is_measured", [False])
@pytest.mark.parametrize(
    "distribution",
    [
        DistributionParameters(name="Normal", sigma=0.05, mu=1.0),
        DistributionParameters(name="Uniform", lower=0.0, upper=2.0),
        DistributionParameters(name="Triangular", lower=-1.0, upper=1.0, mode=0.0),
        DistributionParameters(name="Weibull", parameters=(1.0, 2.0, 0.0)),
        DistributionParameters(name="Exponential", parameters=(1.0, 0.0)),
    ],
)
def test_input_space(tmp_wd, distribution, is_measured):
    """Check that the input space is correctly populated according to the reference input
    data, which can be either measured or described from statistics."""
    nb_samples = 10

    measured_data = Dataset()
    dataset_manipulator = DatasetAddFromStatistics()
    uncertain_input_space = ParameterSpace()
    if is_measured:
        # Add measured inputs. Mock values are obtained from a distribution.
        dataset_manipulator.add_group(
            measured_data,
            IODataset.INPUT_GROUP,
            ["x1"],
            {"x1": distribution},
            nb_samples,
        )
    else:
        add_random_variable_interface(uncertain_input_space, "x1", distribution)

    validation_point_tool = StochasticValidationPoint()
    validation_point_tool._measured_input_names = measured_data.get_variable_names(
        group_name=IODataset.INPUT_GROUP
    )
    expected_input_measured_names = ["x1"] if is_measured else []
    assert validation_point_tool._measured_input_names == expected_input_measured_names

    input_space = validation_point_tool._build_space(
        uncertain_input_space, measured_data
    )
    if distribution.name == "Weibull":
        assert (
            input_space.distributions["x1"].marginals[0].settings["name"]
            == "WeibullMin"
        )
    else:
        assert (
            input_space.distributions["x1"].marginals[0].settings["name"]
            == distribution.name
        )
    assert input_space.uncertain_variables == ["x1"]


def test_end_to_end_stochastic_validation(tmp_wd, validation_point):
    """Check that the simulated data has expected group names and variable names.

    The reference data contains one input measured data, one input data described from
    statistics and one output measured data.
    """
    validation_point_tool, _model, nominal_data = validation_point
    error_dataset = validation_point_tool.result.integrated_metrics

    assert set(error_dataset.keys()) == set(
        validation_point_tool.options["metric_names"]
    )

    simulated_dataset = validation_point_tool.result.simulated_data
    assert simulated_dataset.group_names == ["inputs", "outputs"]
    assert validation_point_tool.result.nominal_data == nominal_data
    # Check that both the measured and uncertain inputs are in the simulated input
    # space:
    assert {"x1", "x1_2"} == set(
        simulated_dataset.get_variable_names(IODataset.INPUT_GROUP)
    )
    assert set(simulated_dataset.get_variable_names(IODataset.OUTPUT_GROUP)) == {"y1"}


def test_report(tmp_wd, validation_point):
    """Check the report of the validation point result."""
    validation_point_tool, model, _ = validation_point
    validation_point_tool.execute(model=model)
    assert set(validation_point_tool.result.metadata.report.keys()) == {
        "title",
        "measured_data_statistics",
        "simulated_uncertainties",
        "typeb_uncertainties",
    }


@pytest.mark.parametrize(
    "plot_type",
    ["PDF", "CDF"],
)
def test_distribution_comparison_plot(tmp_wd, plot_type, validation_point):
    validation_point_tool, _model, _ = validation_point
    plot = DistributionComparison()
    plot.execute(
        validation_point_tool.result,
        "y1",
        plot_type,
        show=False,
        save=True,
    )
    assert (
        plot.working_directory / f"distribution_comparison_{plot_type}_y1.html"
    ).is_file()


def test_plot_results(tmp_wd, validation_point):
    """Check that the plots associated to a ``ValidationPointResult`` are correctly
    generated."""
    validation_point_tool, _model, _ = validation_point
    validation_point_tool.plot_results(
        validation_point_tool.result, "y1", show=False, save=True
    )
    assert (validation_point_tool.working_directory / "qq_plot_y1.png").is_file()
    assert (
        validation_point_tool.working_directory / "distribution_comparison_PDF_y1.html"
    ).is_file()
    assert (
        validation_point_tool.working_directory / "distribution_comparison_CDF_y1.html"
    ).is_file()


@pytest.mark.parametrize("master_value", [2])
def test_read_nominal_values(master_value):
    """Check that nominal values can be computed from a reference data.
    In case of repeats, the nominal value is computed as the mean value of the repeats."""
    nominal_values = read_nominal_values(
        "batch",
        csv_path=VALIDATION_DATA_DIR / "nominal_values.csv",
        master_value=master_value,
        additional_names=["nominal_length"],
    )
    if master_value is None:
        assert_array_equal(nominal_values["batch"], array([1, 2]))
        assert_array_equal(nominal_values["nominal_length"], array([2.0, 3.0]))
    else:
        assert_array_equal(nominal_values["batch"], array([2]))
        assert_array_equal(nominal_values["nominal_length"], array([3.0]))
