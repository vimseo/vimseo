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
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.api import create_model
from vimseo.problems.beam_analytic.reference_dataset_builder import (
    bending_test_analytical_reference_dataset,
)
from vimseo.problems.mock.mock_reference_data.mock_main_reference_functions import (
    mock_model_lc1_overall_function,
)
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.plot_factory import PlotFactory
from vimseo.tools.verification.verification_result import VerificationResult
from vimseo.tools.verification.verification_vs_data import CodeVerificationAgainstData
from vimseo.utilities.datasets import Variable
from vimseo.utilities.datasets import dataset_to_dataframe
from vimseo.utilities.datasets import generate_dataset

BIAS = 0.5


@pytest.fixture
def reference_data():
    """Create a reference IOdataset based on :class:`.MockModel`. The input-output
    relationship corresponds to MockModel with an added bias.

    Also write the data to a csv file.
    """
    group_names_to_vars = {
        IODataset.INPUT_GROUP: [Variable("x1", 1.0, is_constant_value=True)],
        IODataset.OUTPUT_GROUP: [
            Variable(
                "y1",
                mock_model_lc1_overall_function(1.0) + BIAS,
                is_constant_value=True,
            )
        ],
    }
    return generate_dataset(group_names_to_vars, 3)


@pytest.fixture
def parameter_space():
    """Create a space of parameters with scalar variable ``x1`` uniformly distributed
    over [-1, 1]."""
    parameter_space = ParameterSpace()
    parameter_space.add_random_variable(
        "x1", "OTUniformDistribution", size=1, lower=-1.0, upper=1.0
    )
    return parameter_space


@pytest.fixture
def verificator():
    """Create a verification object based on BendingTestAnalytical, acting on scalar
    outputs only."""
    load_case = "Cantilever"
    reference_data = bending_test_analytical_reference_dataset(
        shift=0.5, mult_factor=1.05
    )[load_case]

    verificator = CodeVerificationAgainstData(
        directory_naming_method=DirectoryNamingMethod.NUMBERED,
    )
    verificator.options["metric_names"] = [
        "SquaredErrorMetric",
        "RelativeErrorMetric",
    ]

    model = create_model("BendingTestAnalytical", load_case)
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    output_names = model.get_output_data_names(remove_metadata=True)
    # Remove vector outputs.
    for name in ["moment_grid", "moment", "dplt", "dplt_grid"]:
        output_names.remove(name)
    # TODO add option to restrain verification to model or data outputs?
    output_names.remove("location_max_dplt")
    output_names.remove("maximum_dplt")

    verificator.execute(
        model=model, reference_data=reference_data, output_names=output_names
    )

    return verificator


def test_result_metadata(tmp_wd, reference_data):
    """Check the metadata of a verification result."""
    case_description = {
        "title": "Verification of a cantilever analytic beam for a variation of"
        " beam height.",
        "element_wise": ["Small height value", "High height value"],
    }
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    result = VerificationResult()
    result._fill_metadata(case_description, model.description)
    assert result.description == case_description
    assert result.metadata.model == model.description


def test_error_metric_histogram(tmp_wd, verificator):
    """Check the verification plots."""
    plot = PlotFactory().create("ErrorMetricHistogram")
    plot.working_directory = verificator.working_directory
    plot.execute(
        verificator.result.element_wise_metrics,
        "RelativeErrorMetric",
        "dplt_at_force_location",
        show=False,
        save=True,
    )
    assert (
        verificator.working_directory
        / "metric_histogram_RelativeErrorMetric_dplt_at_force_location.html"
    ).is_file()


def test_error_scatter_matrix(tmp_wd, verificator):
    """Check the validation plots."""
    plot = PlotFactory().create("ErrorScatterMatrix")
    plot.working_directory = verificator.working_directory
    df = dataset_to_dataframe(
        verificator.result.element_wise_metrics, suffix_by_group=True
    )
    plot.execute(
        df,
        "RelativeErrorMetric",
        "dplt_at_force_location",
        show=False,
        save=True,
    )
    assert (
        verificator.working_directory
        / "error_scatter_matrix_RelativeErrorMetric_dplt_at_force_location.html"
    ).is_file()


def test_plot(tmp_wd, verificator):
    """Check the ``plot_result`` method."""
    verificator.save_results()
    result = BaseTool.load_results(
        verificator.working_directory / "CodeVerificationAgainstData_result.pickle"
    )
    output_name = "dplt_at_force_location"
    metric_name = "SquaredErrorMetric"
    verificator.plot_results(
        result,
        metric_name,
        output_name,
        save=True,
        show=False,
    )
    assert (
        verificator.working_directory
        / f"scatter_matrix_{metric_name}_{output_name}.html"
    )
    assert verificator.working_directory / f"integrated_{metric_name}_bars.html"
    assert (
        verificator.working_directory
        / f"metric_histogram_{metric_name}_{output_name}.html"
    )
