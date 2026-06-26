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

import logging
from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from gemseo.datasets.io_dataset import IODataset
from gemseo.utils.directory_creator import DirectoryNamingMethod
from numpy import array
from numpy import mean
from numpy import vstack
from pydantic import Field

from vimseo.config.global_configuration import _configuration as config
from vimseo.direct_measures.curve_measure import DirectMeasureOnCurveSettings
from vimseo.direct_measures.direct_measure_factory import DirectMeasureFactory
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.calibration.direct_measures_result import DirectMeasuresResult
from vimseo.utilities.curves import Curve

if TYPE_CHECKING:
    from pathlib import Path


LOGGER = logging.getLogger(__name__)


class DirectMeasuresSettings(BaseSettings):
    direct_measure_settings: Mapping[str, DirectMeasureOnCurveSettings] = Field(
        default={},
        description="A mapping of measure_names to settings of a direct measure on a curve.",
    )


# class StreamlitMetricDirectCalibrationStepSettings(MetricDirectCalibrationStepSettings):


class DirectMeasuresInputs(BaseInputs):
    reference_data: IODataset | None = Field(
        default=None,
        description="The reference [IODataset][gemseo.datasets.io_dataset.IODataset]"
        "against which the model is compared "
        "to find the best measures. Several reference samples can be "
        "provided as rows of the dataset.",
    )


class DirectMeasures(BaseAnalysisTool):
    """A calibration step to identify material properties based on direct measures on
    experimental data.

    A step means that the best measures are searched to match model outputs against N
    test results for a single load case.
    """

    _INPUTS = DirectMeasuresInputs

    _SETTINGS = DirectMeasuresSettings

    # _STREAMLIT_SETTINGS = StreamlitMetricDirectCalibrationStepSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )
        self.result = DirectMeasuresResult()

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: DirectMeasuresInputs | None = None,
        settings: DirectMeasuresSettings | None = None,
        **options,
    ) -> DirectMeasuresResult:

        reference_data = options["reference_data"]
        measures = defaultdict(list)

        for measure_name, measure_settings in options[
            "direct_measure_settings"
        ].items():
            for sample_id in range(reference_data.shape[0]):
                values = vstack([
                    reference_data.get_view(
                        variable_names=[
                            measure_settings["x_name"],
                        ]
                    ).to_numpy()[sample_id],
                    reference_data.get_view(
                        variable_names=[
                            measure_settings["y_name"],
                        ]
                    ).to_numpy()[sample_id],
                ]).T
                curve = Curve({
                    measure_settings["x_name"]: values[:, 0],
                    measure_settings["y_name"]: values[:, 1],
                })
                measures[measure_name].append(
                    DirectMeasureFactory()
                    .create(measure_settings["measure_name"])
                    .compute(curve)
                )
            measures[measure_name] = array(measures[measure_name])

        self.result.direct_measures = measures
        self.result.mean_direct_measures = {
            name: mean(measure) for name, measure in measures.items()
        }
