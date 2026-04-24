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

from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from gemseo.datasets.dataset import Dataset
from gemseo.uncertainty import create_statistics
from gemseo.uncertainty.statistics.parametric_statistics import ParametricStatistics
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import random
from numpy import vstack
from pydantic import Field
from statsmodels.distributions import ECDF

from vimseo.config.global_configuration import _configuration as config
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.statistics.statistics_result import StatisticsResult
from vimseo.utilities.datasets import dataset_to_dataframe
from vimseo.utilities.datasets import get_scalar_names

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pandas import DataFrame
    from plotly.graph_objs import Figure


class StatisticsInputs(BaseInputs):
    dataset: Dataset | None = None


class StatisticsSettings(BaseSettings):
    variable_names: list[str] = Field(
        default=[],
        description="The variables of interest. If left to default value, "
        "consider all the variables from the input dataset.",
    )
    fitting_criterion: str = Field(
        default="Kolmogorov",
        description="The name of a goodness-of-fit criterion, "
        "measuring how the distribution fits the data. "
        "Use :meth:`.ParametricStatistics.get_criteria` "
        "to get the available criteria.",
    )
    selection_criterion: str = Field(
        default="best",
        description="The name of a selection criterion "
        "to select a distribution from candidates. "
        "Either 'first' or 'best'.",
    )
    level: float = Field(
        default=0.05,
        description="A test level, i.e. the risk of committing a Type 1 error, "
        "that is an incorrect rejection of a true null hypothesis, "
        "for criteria based on a test hypothesis.",
    )
    tested_distributions: list[str] = Field(
        default=[
            "Uniform",
            "Normal",
            "LogNormal",
            "Exponential",
            "WeibullMin",
        ],
        description="The names of the tested distributions.",
    )
    coverage: float = Field(
        default=0.05,
        description="A minimum percentage of belonging to a tolerance interval.",
    )
    confidence: float = Field(
        default=0.95, description="A level of confidence in [0,1]."
    )


class StatisticsTool(BaseAnalysisTool):
    """Provide methods for calculating Parametric and Empirical statistics for a given
    dataset.

    Advanced users can change the default toolset parameters to tool specific
    (user-defined) parameters, by passing options to :meth:`execute`.
    """

    result: StatisticsResult

    _INPUTS = StatisticsInputs

    _SETTINGS = StatisticsSettings

    _STREAMLIT_SETTINGS = StatisticsSettings

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
            **options,
        )
        self._dataset = None
        self.result = StatisticsResult()

    @staticmethod
    def build_distributions(distributions):
        """Build distributions from a list of distributions names, a test level and the
        stored dataset.

        Args:
            distributions: list of distributions names.
        """
        return ParametricStatistics.build_distributions(distributions)

    @BaseTool.validate
    def execute(
        self,
        inputs: StatisticsInputs | None = None,
        settings: StatisticsSettings | None = None,
        **options,
    ) -> StatisticsResult:
        """Create a statistics toolbox, either parametric or empirical, based on gemseo
        capabilities.

        If parametric, the toolbox selects a distribution from candidates, based on a
        fitting criterion and on a selection strategy.

        It also computes statistics from the gemseo statistics toolbox based  on the
        default values given in the statistics_tool_defaults dictionary
        """
        dataset = options["dataset"]
        self._dataset = dataset

        # Perturb constant samples to avoid error in OpenTurns
        scalar_names = []
        for group_name in dataset.group_names:
            scalar_names += get_scalar_names(dataset, group_name)
        df = dataset_to_dataframe(dataset, variable_names=scalar_names)
        constant_df = df.loc[:, (df == df.iloc[0]).all()]
        constant_df = constant_df.select_dtypes([np.number])
        for constant_name in constant_df.columns:
            df[constant_name] = df[constant_name] * (
                1 + 1e-6 * random.uniform(-1, 1, size=len(df[constant_name]))  # noqa: NPY002
            )

        analysis = create_statistics(
            Dataset.from_dataframe(df),
            name=self.name,
            variable_names=options["variable_names"],
            tested_distributions=options["tested_distributions"],
            fitting_criterion=options["fitting_criterion"],
            selection_criterion=options["selection_criterion"],
            level=options["level"],
        )

        self.result.analysis = analysis
        self.result.statistics = self.compute_all_statistics(as_df=False)
        self.result.best_fitting_distributions = {
            name: analysis.distributions[name].name
            for name in list(analysis.distributions.keys())
        }
        return self.result

    @staticmethod
    def get_criteria(varname):
        """Get criteria for a given variable name.

        :param str varname: variable name.
        """
        return ParametricStatistics.get_criteria(varname)

    @staticmethod
    def get_fitting_matrix():
        """Get the fitting matrix.

        This matrix contains goodness-of-fit measures for each pair < variable,
        distribution >.
        """
        return ParametricStatistics.get_fitting_matrix()

    @staticmethod
    def get_available_distributions():
        """Get available distributions."""
        return ParametricStatistics.get_fitting_matrix()

    @staticmethod
    def get_available_criteria():
        """Get available goodness-of-fit criteria."""
        return ParametricStatistics.get_available_criteria()

    @staticmethod
    def get_significance_tests():
        """Get significance adapter."""
        return ParametricStatistics.get_significance_tests()

    def compute_all_statistics(self, as_df=True) -> OrderedDict | DataFrame:
        """Provides a summary of the statistics currently available in gemseo.

        Args:
            as_df: if True the results are returned in the form of a pandas dataframe,
            else as a dictionary. Default: False

        Returns:
            a Pandas Dataframe or OrderedDict() with the computed statistics
        """
        compute = [
            ("maximum", self.result.analysis.compute_maximum, {}),
            ("minimum", self.result.analysis.compute_minimum, {}),
            ("range", self.result.analysis.compute_range, {}),
            ("mean", self.result.analysis.compute_mean, {}),
            ("median", self.result.analysis.compute_median, {}),
            (
                "compute_standard_deviation",
                self.result.analysis.compute_standard_deviation,
                {},
            ),
            ("variance", self.result.analysis.compute_variance, {}),
            ("percentile_5", self.result.analysis.compute_percentile, {"order": 5}),
            ("percentile_10", self.result.analysis.compute_percentile, {"order": 10}),
            ("percentile_25", self.result.analysis.compute_percentile, {"order": 25}),
            ("percentile_50", self.result.analysis.compute_percentile, {"order": 50}),
            ("percentile_75", self.result.analysis.compute_percentile, {"order": 75}),
            ("percentile_90", self.result.analysis.compute_percentile, {"order": 90}),
            ("percentile_95", self.result.analysis.compute_percentile, {"order": 95}),
            (
                "tolerance_interval",
                self.result.analysis.compute_tolerance_interval,
                {
                    "coverage": self._options["coverage"],
                    "confidence": self._options["confidence"],
                },
            ),
            ("a_value", self.result.analysis.compute_a_value, {}),
            ("b_value", self.result.analysis.compute_b_value, {}),
        ]

        results = OrderedDict()
        for func_name, key, value in compute:
            for func, kwargs in zip([key], [value], strict=False):
                try:
                    r = func(**kwargs)
                    results[func_name] = r
                except (
                    KeyError,
                    TypeError,
                    NotImplementedError,
                    AttributeError,
                    ImportError,
                ) as e:
                    print(e)

        return pd.DataFrame.from_dict(results) if as_df else results

    def plot_results(
        self,
        result: StatisticsResult,
        save=False,
        show=True,
        directory_path: str | Path = "",
        variable=None,
    ) -> Mapping[str, Figure]:
        """Plot criteria for a given variable name.

        Args:
            variable: The name of the variable whose statistics are shown.
        """
        return result.analysis.plot_criteria(
            variable=variable,
            title="Criteria of statistics.",
            save=save,
            show=show,
            directory=(
                self.working_directory if directory_path == "" else Path(directory_path)
            ),
            fig_size=(12.0, 6.0),
        )


def compute_ecdf(input_data: Dataset, prefix: str = "") -> Dataset:
    """Compute the empirical CDF of a dataset. The ECDF are stored in a dataset, where
    each ECDF is in a different group containing two variables: name_x and name_y
    where name is the name of the variable on which the ECDF is computed.

    Args:
        input_data: The input dataset.
        prefix: A prefix for the variable names in the output dataset.

    Returns: A dataset containing the ECDF.

    """
    input_data = input_data.to_dict_of_arrays()
    variable_names = []
    data = []
    variable_names_to_group_names = {}
    for group_name, group_data in input_data.items():
        for name in group_data:
            x = input_data[group_name][name].flatten()
            ecdf = ECDF(x)
            ecdf_variable_names = [f"{prefix}_{name}_x", f"{prefix}_{name}_y"]
            variable_names.extend(ecdf_variable_names)
            data.extend([ecdf.x, ecdf.y])
            variable_names_to_group_names.update({
                ecdf_variable_names[0]: group_name,
                ecdf_variable_names[1]: group_name,
            })
    return Dataset.from_array(
        data=vstack(data).T,
        variable_names=variable_names,
        variable_names_to_group_names=variable_names_to_group_names,
    )
