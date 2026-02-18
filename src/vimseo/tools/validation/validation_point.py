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

import logging
from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from gemseo.utils.metrics.metric_factory import MetricFactory
from numpy import array
from numpy import atleast_1d
from numpy import mean
from numpy import ndarray
from pandas import DataFrame
from pandas import read_csv
from pydantic import ConfigDict
from pydantic import Field
from statsmodels.graphics.gofplots import qqplot_2samples
from strenum import StrEnum

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.doe.doe import DOESettings
from vimseo.tools.doe.doe import DOETool
from vimseo.tools.post_tools.distribution_comparison_plot import DistributionComparison
from vimseo.tools.space.space_tool import update_space_from_statistics
from vimseo.tools.statistics.statistics_tool import StatisticsInputs
from vimseo.tools.statistics.statistics_tool import StatisticsSettings
from vimseo.tools.statistics.statistics_tool import StatisticsTool
from vimseo.tools.validation.validation_point_result import ValidationPointResult
from vimseo.utilities.datasets import dataframe_to_dataset
from vimseo.utilities.encoded_to_numerical_vectors import decode_stringified_vectors

if TYPE_CHECKING:
    from collections.abc import Iterable

    from plotly.graph_objs import Figure


LOGGER = logging.getLogger(__name__)


class StochasticValidationPointInputs(BaseInputs):
    model: IntegratedModel | None = None

    measured_data: Dataset | None = None
    """The dataset containing the validation test samples."""

    uncertain_input_space: ParameterSpace = Field(
        default=ParameterSpace(),
        description="A parameter space of the non-measured input variables.",
    )


class StochasticValidationPointSettings(DOESettings, StatisticsSettings):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    metric_names: list[str] = Field(
        default=["AbsoluteRelativeErrorP90", "RelativeMeanToMean"],
        description="The default statistical metrics used for stochastic validation.",
    )
    simulated_uncertainties: Mapping[str, float] = Field(
        default_factory=dict,
        description="A dictionary mapping output name to an uncertainty "
        "inherent to the model (standard deviation), "
        "typically estimated from verification studies.",
    )
    output_names: list[str] = Field(
        default=[],
        description="The names of the output on which validation is performed. "
        "By default, consider all the outputs of the reference samples.",
    )
    nominal_data: Mapping[str, float | int | ndarray] = Field(
        default_factory=dict,
        description="The nominal value of the input variables.",
    )
    typeb_uncertainties: Mapping[str, float] = Field(
        default_factory=dict,
        description="A mapping variable names (either inputs or QoI) "
        "to type B value, defined as the standard deviation of the measurement.",
    )


class StochasticValidationPoint(BaseAnalysisTool):
    """Suppose we want to validate a model ove a given validation domain.

    We define validation point as one of the points chosen to map this domain.
    """

    name: str
    """The name of the validation point."""

    results: ValidationPointResult

    _INPUTS = StochasticValidationPointInputs

    _SETTINGS = StochasticValidationPointSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
        **options,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
            subtools=[DOETool(), StatisticsTool()],
            **options,
        )

        self._simulated_input_space = None
        self._measured_statistic_results = None

        self.result = ValidationPointResult()

    @property
    def simulated_input_space(self) -> ParameterSpace:
        """The simulated input parameter space."""
        return self._simulated_input_space

    @property
    def measured_input_space(self) -> ParameterSpace:
        """The measured input parameter space."""
        return self._measured_input_space

    def _build_space(
        self,
        uncertain_input_space: ParameterSpace,
        measured_data: IODataset,
        model: IntegratedModel | None = None,
        settings: StatisticsSettings | None = None,
    ) -> ParameterSpace:
        """Build space of parameters for validation on uncertain variables."""
        statistics_tool = self._subtools["StatisticsTool"]
        uncertain_space_with_measured_variables = deepcopy(uncertain_input_space)
        # Second, add the measured variables. Fit their distribution from the measured_data.
        if self._measured_input_names:
            self._measured_statistic_results = statistics_tool.execute(
                inputs=StatisticsInputs(dataset=measured_data), settings=settings
            )
            self.result.metadata.report["measured_data_statistics"] = repr(
                statistics_tool.result
            )
            update_space_from_statistics(
                uncertain_space_with_measured_variables,
                statistics_tool.result,
                model=model,
            )

        return uncertain_space_with_measured_variables

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: StochasticValidationPointInputs | None = None,
        settings: StochasticValidationPointSettings | None = None,
        **options,
    ) -> ValidationPointResult:
        """Compute the errors between reference data and simulated data for the
        prescribed error measures."""

        measured_data = options["measured_data"]
        nominal_data = options["nominal_data"]
        uncertain_input_space = options["uncertain_input_space"]

        self._measured_input_names = measured_data.get_variable_names(
            group_name=IODataset.INPUT_GROUP
        )

        model = options["model"]
        model.default_input_data.update({
            name: atleast_1d(value)
            for name, value in nominal_data.items()
            if name in model.default_input_data
        })

        self.result.metadata.report["title"] = (
            f"Validation of {model.name} {model.load_case.name}"
        )
        self.result.metadata.model = model.description
        self.result.metadata.report["simulated_uncertainties"] = options[
            "simulated_uncertainties"
        ]
        self.result.metadata.report["typeb_uncertainties"] = options[
            "typeb_uncertainties"
        ]

        measured_output_names = (
            measured_data.get_variable_names(group_name=IODataset.OUTPUT_GROUP)
            if len(options["output_names"]) == 0
            else options["output_names"]
        )
        self.result.metadata.report["measured_output_names"] = measured_output_names

        self.result.measured_data = measured_data
        self.result.nominal_data = nominal_data

        statistics_settings = deepcopy(options)
        statistics_settings.update({"variable_names": self._measured_input_names})
        statistics_settings = StatisticsTool().get_filtered_options(
            **statistics_settings
        )
        self._simulated_input_space = self._build_space(
            uncertain_input_space,
            measured_data,
            model=model,
            settings=StatisticsSettings(**statistics_settings),
        )

        doe_dataset = (
            self
            ._subtools["DOETool"]
            .execute(
                model=model,
                parameter_space=self._simulated_input_space,
                output_names=measured_output_names,
                n_samples=options["n_samples"],
                algo=options["algo"],
                # algo_options=options["algo_options"],
            )
            .dataset
        )
        for metric_name in options["metric_names"]:
            metric = MetricFactory().create(metric_name)
            self.result.integrated_metrics[metric_name] = {}
            for output_name in measured_output_names:
                self.result.integrated_metrics[metric_name][output_name] = (
                    metric.compute(
                        doe_dataset
                        .get_view(variable_names=output_name)
                        .to_numpy()
                        .ravel(),
                        measured_data
                        .get_view(variable_names=output_name)
                        .to_numpy()
                        .ravel(),
                    )
                )

        self.result.simulated_data = doe_dataset
        return self.result

    def plot_results(
        self,
        result: ValidationPointResult,
        output_name: str,
        directory_path: str | Path = "",
        save=False,
        show=True,
        file_format="html",
    ) -> Mapping[str, Figure]:
        """Plot a comparison of predicted versus measured distribution, and a Q-Q plot of
        them.

        Args:
            result: The validation point result to visualize.
            output_name: The name of the output variable to visualize.
            file_format: The format to which plots are generated.
        """
        working_directory = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )

        figures = {}

        plot = DistributionComparison(working_directory=working_directory)
        for comparison_type in ["PDF", "CDF"]:
            figures[f"{comparison_type}_comparison"] = plot.execute(
                result,
                output_name,
                comparison_type,
                show_type_b_uncertainties=True,
                show=show,
                save=save,
            ).figure

        data_ref = result.measured_data.to_dict_of_arrays(by_group=False)[
            output_name
        ].ravel()
        data_sim = result.simulated_data.to_dict_of_arrays(by_group=False)[
            output_name
        ].ravel()

        fig = qqplot_2samples(
            data_ref,
            data_sim,
            ylabel="Simulated",
            xlabel="Reference",
            line="45",
        )

        if show:
            plt.show()
        if save:
            plt.savefig(working_directory / f"qq_plot_{output_name}.png")

        figures["qq_plot"] = fig

        return figures


class NominalValuesOutputType(StrEnum):
    """The type of the nominal values returned by ```read_nominal_values()``."""

    DATAFRAME = "dataframe"
    GEMSEO_DATASET = "gemseo_dataset"
    DICTIONARY = "dictionary"


def read_nominal_values(
    master_name: str,
    csv_path: str | Path = "",
    df: DataFrame | None = None,
    master_value: float | None = None,
    additional_names: Iterable[str] = (),
    name_remapping: Mapping[str, str] | None = None,
    delimiter: str = ";",
    output_type: NominalValuesOutputType = NominalValuesOutputType.DATAFRAME,
    variable_names_to_group_names: Mapping[str, str] | None = None,
    vector_names_to_group_names: Mapping[str, str] | None = None,
    stringified_vector_separator: str = "_",
) -> Mapping[str, ndarray] | DataFrame:
    """Creates a dictionary of nominal values based on a reference data.

    Since several specimens are tested for a given nominal point (typically a layup),
    this function:
      - makes unique the list of values corresponding to the ``master_name`` variable.
      - optionally filters the data for a given value of ``master_name``.
      - for each ``master_name`` value, it reads the associated ``additional_keys``
        These additional_keys are made unique for each layup
        by taking the mean value of all specimens associated to this ``master_name``
        value.
    Vectors are assumed to be encoded into strings, typically [0, 4, 7] => "0_4_7"

    Args:
        csv_path: The path to the csv file.
        df: The dataframe containing the data. If no csv_path is provided,
        this data is used.
        master_name: The name of variable that will be made unique,
            such that only one nominal value is associated with a batch of
            tests.
        master_value: If set as a float, the nominal values are returned only for this
            value of ``master_name``.
        additional_names: The names that will be added to the nominal variables,
            in addition to the master_name. They are computed as the mean
            value of each batch values. If empty, consider all variables.
        name_remapping: A mapping to rename the variables
            ``master_name`` and ``additional_names`` read in the csv file.
            It is useful to obtain nominal variable names compatible with a model.
        delimiter: The delimiter of the csv data.
        output_type: The type in which the nominal values are returned.
        variable_names_to_group_names: A mapping between a variable name and
            its group name. Must be defined for each variable among
            {master_name, additional_names}
            if output_type=NominalValuesOutputType.GEMSEO_DATASET.
            Unused otherwise.
        vector_names_to_group_names: a mapping between a variable name and its
            group name. The specified vectors, encoded as strings in the input data,
            are decoded as arrays of numerical values and added to the output dataset.
            The original encode variables are renamed with the ``_stringified`` suffix.
            Only used for output_type=NominalValuesOutputType.GEMSEO_DATASET.
        stringified_vector_separator: The separator used in the stringified vectors
            in the input data, typically ``_`` for vectors represented as
            ``"1_4_7"``.

    Returns:
        Either a Pandas.DataFrame (mono-indexed column), a GEMSEO Dataset,
        or a dictionary of NumPy arrays.
    """

    if csv_path and df is not None:
        raise ValueError("Only one of csv_path and df should be provided.")

    if csv_path:
        df = read_csv(
            csv_path,
            delimiter=delimiter,
        )

    if name_remapping is None:
        name_remapping = {}

    if len(additional_names) == 0:
        additional_names = df.columns.tolist()
        additional_names.remove(master_name)

    if master_value:
        df = df[df[master_name] == master_value]

    nominal_values = defaultdict(list)
    nominal_values[master_name] = df[master_name].unique()

    for val_of_key in nominal_values[master_name]:
        filtered_df = df[df[master_name] == val_of_key]
        for additional_key in additional_names:
            nominal_values[additional_key].append(mean(filtered_df[additional_key]))
    for additional_key in additional_names:
        nominal_values[additional_key] = array(nominal_values[additional_key])

    if output_type == NominalValuesOutputType.GEMSEO_DATASET:
        for name in [*additional_names, master_name]:
            if name in name_remapping:
                name_remapping[name] = (
                    f"{name_remapping[name]}[{variable_names_to_group_names[name]}][0]"
                )
            else:
                name_remapping[name] = (
                    f"{name}[{variable_names_to_group_names[name]}][0]"
                )
    if name_remapping:
        for name, new_name in name_remapping.items():
            if name in nominal_values:
                nominal_values.update({new_name: nominal_values[name]})
                del nominal_values[name]

    if output_type == NominalValuesOutputType.DICTIONARY:
        return nominal_values
    if output_type == NominalValuesOutputType.DATAFRAME:
        return DataFrame.from_dict(nominal_values)
    if output_type == NominalValuesOutputType.GEMSEO_DATASET:
        ds = dataframe_to_dataset(DataFrame.from_dict(nominal_values))
        if vector_names_to_group_names is not None:
            return decode_stringified_vectors(
                ds, vector_names_to_group_names, stringified_vector_separator
            )
        return ds
    msg = f"Invalid output type: {output_type}."
    raise ValueError(msg)
