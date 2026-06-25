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

"""A base class to verify a model."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from gemseo.utils.directory_creator import DirectoryNamingMethod
from gemseo.utils.metrics.dataset_metric import DatasetMetric
from gemseo.utils.metrics.metric_factory import MetricFactory
from numpy import vstack
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.model_metadata import MetaDataNames
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.doe.custom_doe import CustomDOESettings
from vimseo.tools.post_tools.verification_plots import ErrorMetricHistogram
from vimseo.tools.verification.verification_result import CASE_DESCRIPTION_TYPE
from vimseo.tools.verification.verification_result import VerificationResult
from vimseo.utilities.datasets import get_nb_input_variables

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from plotly.graph_objs import Figure

REFERENCE_PREFIX = "Ref"


def convergence_renaming(name):
    """Rename an output variable of a convergence verification."""
    return f"|{name}-extrapol|"


def comparison_renaming(name, prefix=""):
    """Rename an output variable of a code verification."""
    return f"{prefix}[{name}]"


def prepare_overall_dataset(
    result, metric_names, output_names, renamer=None, add_output_data=True
):
    """Prepare the final dataset used in the dashboard.

    Args:
        result: A verification result.
        metric_names: The names of the selected metrics.
        output_names: The names of the selected output variables.
        renamer: A function to rename output variable names to more expressive names and
        also to ensure that the variable names of the final dataset are unique
        (useful to further convert this dataset to mono-index dataframe).
        add_output_data: Whether to add the output variables to the error metrics in
        the final dataset.

    Returns: A dataset containing the inpout variables, the selected metrics with
    unique variable names, and possibly the raw output variables.
    """
    # Rename element-wise metrics to ensure variable names are unique.
    group_names = [IODataset.INPUT_GROUP]
    group_names.extend(metric_names)
    overall_dataset = result.element_wise_metrics.get_view(
        group_names=group_names
    ).copy()
    if renamer:
        for metric_name in metric_names:
            for name in overall_dataset.get_variable_names(group_name=metric_name):
                new_name = renamer(name, metric_name)
                overall_dataset.rename_variable(name, new_name, group_name=metric_name)

    # Drop unused outputs from the metric group
    for metric_name in metric_names:
        for output_name in overall_dataset.get_variable_names(group_name=metric_name):
            if output_name not in [renamer(name, metric_name) for name in output_names]:
                overall_dataset.drop(output_name, axis=1, level=1, inplace=True)

    if add_output_data:
        variable_names = output_names
        name_to_value = {
            name: result.simulation_and_reference
            .get_view(group_names=IODataset.OUTPUT_GROUP, variable_names=name)
            .to_numpy()
            .T
            for name in variable_names
        }
        overall_dataset.add_group(
            IODataset.OUTPUT_GROUP,
            data=vstack([name_to_value[name] for name in variable_names]).T,
            variable_names=variable_names,
            variable_names_to_n_components={
                name: name_to_value[name].shape[0] for name in variable_names
            },
        )

    return overall_dataset


def check_output_names(output_names, model) -> None:
    """Check that the output names to verify are included in the model output names.
    Otherwise, the merror metrics cannot be computed on all the output names.

    Args:
        output_names: The output names to verify.
        model: The model to verify.

    Raises:
        ValueError if ``output_names`` is not included in the model output names.
    """
    if not set(output_names).issubset(model.output_grammar.names):
        raise ValueError(
            msg=f"The outputs to verify {output_names} are not contained in the"
            f"model {model.name} outputs, which are {model.output_grammar.names}"
        )


class BaseCodeVerificationSettings(CustomDOESettings):
    metric_names: list[str] = Field(
        default=["SquaredErrorMetric", "RelativeErrorMetric", "AbsoluteErrorMetric"],
        description="The default metric that applies to all model output variables.",
    )
    description: CASE_DESCRIPTION_TYPE | None = None


class BaseVerification(BaseAnalysisTool):
    """A base class to implement code verification."""

    results: VerificationResult

    metric_names: Iterable[str]
    """The name of the metrics used to compute the error between predictions and
    references."""

    def __init__(
        self,
        subtools,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        super().__init__(
            subtools=subtools,
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )
        self._output_names = []
        self.result = VerificationResult()

    def _compute_comparison(
        self, reference_data, doe_dataset
    ) -> tuple[Dataset, Mapping[str : Mapping[str:float]]]:
        """Compare reference and DOE datasets using the metrics defined by
        :attr:`metric_names`.

        Args:
            reference_data: A Dataset containing at least the variables of the
            ``doe_dataset`` output group.
            doe_dataset: An ``IODataset``.

        Returns: A tuple where first element is the element wise metric, and second element
        is a dictionary containing the integrated metric values.
        """

        # TODO If output_names setting is left to default value,
        #  there is an arbitrary choice that the compared variable are taken
        #  from the DOE (So the comparison is restrained to the model outputs, and we
        #  assume that the reference output names contain at least all the model output
        #  names.).
        #  Conversely, it could be restrained to the reference output names.
        #  Or, we could consider the intersection between the model output names and the
        #  reference output names.
        # Each metric is applied to all output_names
        integrated_metrics = {}
        error_dataset = Dataset()
        for metric_name in self.options["metric_names"]:
            metric = MetricFactory().create(metric_name)
            dm = DatasetMetric(
                metric,
                variable_names=self._output_names,
            )
            error_ds = dm.compute(doe_dataset, reference_data)
            error_dataset.add_group(
                group_name=metric_name,
                variable_names=self._output_names,
                data=error_ds.get_view().to_numpy(),
                variable_names_to_n_components=error_ds.group_names_to_n_components,
            )
            integrated_metrics[metric_name] = {}
            for output_name in self._output_names:
                dm = DatasetMetric(
                    metric,
                    variable_names=output_name,
                )
                mean_metric = MetricFactory().create("MeanMetric", dm)
                integrated_metrics[metric_name][output_name] = mean_metric.compute(
                    doe_dataset,
                    reference_data,
                )

        return error_dataset, integrated_metrics

    def _post(
        self,
        doe_dataset: Dataset,
        reference_data: Dataset,
        element_wise_metrics: Dataset,
    ) -> tuple[IODataset, Dataset]:
        """Concatenate the reference and DOE datasets, ensuring the output variable names
        are unique: the reference output variables are renamed according to
        :meth:`comparison_renaming`.
        Concatenate the input variables (group ``IODataset.INPUT_GROUP`` of the
        reference dataset) with the metrics.

        Args:
            doe_dataset: An ``IODataset`` containing the DOE results.
            reference_data: An ``IODataset`` containing the reference data.
            element_wise_metrics: A ``Dataset`` containing the element-wise metric values.

        Returns: A tuple where first element is:
        - an ``IODataset`` containing the reference input variables, the DOE output
           variables and the reference output variables renamed according to convection
           ``Ref[variable_name]``.
        - a ``Dataset`` containing the reference input variables and the element-wise
         metric values for each output variables, each metric being stored in a
          dedicated group having same name as the metric.
        """

        # Concatenate simulated and ref data.
        reference_outputs = reference_data.get_view(
            group_names=IODataset.OUTPUT_GROUP, variable_names=self._output_names
        ).rename(
            columns={
                name: comparison_renaming(name, REFERENCE_PREFIX)
                for name in reference_data.get_variable_names(
                    group_name=IODataset.OUTPUT_GROUP
                )
            }
        )
        reference_outputs.index = doe_dataset.index
        simulation_and_reference = pd.concat(
            [
                doe_dataset,
                reference_outputs,
            ],
            axis=1,
        )

        # TODO Rather concat input vars and metrics in the Comparator?
        group_names = [IODataset.INPUT_GROUP]
        group_names.extend(self.options["metric_names"])
        element_wise_metrics.index = doe_dataset.index
        return simulation_and_reference, pd.concat(
            [doe_dataset, element_wise_metrics],
            axis=1,
        ).get_view(group_names=group_names)

    def plot_results(
        self,
        result: VerificationResult,
        metric_name,
        output_name: str,
        save=False,
        show=True,
        directory_path: str | Path = "",
        file_format="html",
    ) -> Mapping[str, Figure]:
        """Plot a line plot of simulated versus reference results, and a bar plot of
        metrics values.

        Args:
            metric_name: The name of the metric to visualize.
            output_name: The name of the output variable to visualize.
            file_format: The format to which plots are generated.
        """
        working_directory = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )

        figures = {}

        if metric_name:
            ds = prepare_overall_dataset(
                result,
                [metric_name],
                result.simulation_and_reference.get_variable_names(
                    IODataset.OUTPUT_GROUP
                ),
                renamer=comparison_renaming,
                add_output_data=True,
            )
        else:
            ds = result.element_wise_metrics

        if get_nb_input_variables(result.element_wise_metrics) > 1:
            scatter_matrix = ScatterMatrix(
                ds,
                variable_names=result.element_wise_metrics.get_variable_names(
                    group_name=IODataset.INPUT_GROUP
                ),
                kde=False,
            )
            fig = scatter_matrix.execute(
                save=save,
                show=show,
                file_format="png",
                directory_path=(
                    self.working_directory
                    if directory_path == ""
                    else Path(directory_path)
                ),
                file_name="scatter_matrix",
            )[0]
            figures["input_scatter_matrix"] = fig

        histogram = ErrorMetricHistogram()
        histogram.working_directory = (
            working_directory if directory_path == "" else Path(directory_path)
        )
        histogram.execute(
            result.element_wise_metrics, metric_name, output_name, show=show, save=save
        )
        figures["error_metric_histogram"] = histogram.result.figure

        return figures

    # TODO this method is temporary until metadata variables contain only the
    #  cpu time. Then, if ``output_names`` setting is left to default value,
    #  the output names will contain the cpu time, since obtained from
    #  model.get_output_data().
    def get_extended_output_names(self):
        """Adds the CPU_TIME metadata variable name to the output names."""
        return (
            [*self._output_names, MetaDataNames.cpu_time]
            if [MetaDataNames.cpu_time] not in self._output_names
            else self._output_names
        )
