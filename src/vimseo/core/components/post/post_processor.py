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
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

import matplotlib.pyplot as plt
import numpy as np
from numpy import array
from numpy import atleast_1d
from numpy import interp
from numpy import linspace
from numpy import nan

import vimseo.lib_vimseo.solver_utilities as utils
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.core.model_metadata import MetaDataNames

if TYPE_CHECKING:
    from collections.abc import Iterable

    from numpy import ndarray

    from vimseo.core.load_case import LoadCase
    from vimseo.material.material import Material

LOGGER = logging.getLogger(__name__)


class PostProcessor(ExternalSoftwareComponent):
    """Class defining library of components dedicated to post-processing.

    _run method to be overloaded.
    """

    del_jobdir: bool
    """Whether to delete the job directory after post-processing."""

    DELETE_JOB_DIR: bool = False
    """If True deletes the Abaqus job directory after post-processing."""

    _OUTPUTS_TO_RESAMPLE: ClassVar[Iterable[str]] = []
    """List of names of curves outputs to be resampled into a specific size."""

    _RESAMPLING_OUTPUT_SIZE = 100
    """Number of points to have on resampled curves."""

    def __init__(
        self,
        load_case: LoadCase | None = None,
        material_grammar_file: Path | str = "",
        material: Material | None = None,
        check_subprocess: bool = False,
    ) -> None:
        super().__init__(load_case, material_grammar_file, material, check_subprocess)

        self._output_physical_var_names = set(self.output_grammar.names) - {
            self._ERROR_CODE_NAME
        }
        self.output_grammar.update_from_data({
            MetaDataNames.error_code.name: atleast_1d(
                IntegratedModel._ERROR_CODE_DEFAULT
            )
        })

    def _run(self, input_data):
        raise NotImplementedError

    def plot_output_data(self, data, x_data, y_data, save_path, save, show, fig_id):
        """Plot output data of post-processor.

        Args:
            data: The DisciplineData to plot
            x_data: name of x axis data
            y_data: name of y axis data
            save_path: path where the figure is saved
            save: Whether to save the plot
            show: Whether to show the plot
            fig_id: the id of the figure

        Returns:
            None
        """
        plt.figure(fig_id)
        x = data[x_data]
        y = data[y_data]
        plt.plot(x, y)
        plt.xlabel(x_data)
        plt.ylabel(y_data)
        if save:
            plt.savefig(Path(save_path) / f"{x_data}_{y_data}_{fig_id}.png")
        if show:
            plt.show()

    def evaluate_modulus_10_50(
        self,
        strain_history: ndarray,
        stress_history: ndarray,
        strain_at_max_strength: float | None = None,
    ):
        """Evaluate the modulus between 10 % and 50 % of the maximum strength. Maximum
        strength can be provided as a reference value If max_strength is None, else the
        maximum strength is estimated from the stress_history. The maximum strength is
        computed as the maximum of the stress history for a tension configuration, or the
        minimum for a compression config. The tension or compression configuration
        is determined thanks to the sign of the stress in the middle of the history.

        Args:
            strain_history: array of strain data
            stress_history: array of stress data
            strain_at_max_strength: ultimate strain considered for the calculation
        """

        if strain_at_max_strength is None:
            if stress_history[int(len(stress_history) / 2)] > 0:
                index_max_strength = np.argmax(stress_history)
            else:
                index_max_strength = np.argmin(stress_history)

            strain_at_max_strength = strain_history[index_max_strength]

        return utils.local_slope_computation(
            strain_history,
            stress_history,
            x_min=0.10 * strain_at_max_strength,
            x_max=0.50 * strain_at_max_strength,
            method="regression",
        )

    def evaluate_modulus_e005_e025(self, strain_history, stress_history):
        """Evaluate the modulus between 0.0005 and 0.0025 strain (500 and 2500 micro-
        def).

        :param strain_history: array of strain data
        :param stress_history: array of stress data
        """

        return utils.local_slope_computation(
            strain_history,
            stress_history,
            x_min=0.0005,
            x_max=0.0025,
            method="average",
        )

    def _generate_nan_outputs(self):
        """Generates dummy outputs for all outputs expected by the output grammar of this
        component.

        This is useful in case of any error in the model workflow, to get valid dummy
        outputs that pass the output grammar.
        """

        jsondata = self.output_grammar.schema
        output_data = {}

        for key in jsondata["properties"]:
            var_type = jsondata["properties"][key]["items"].get("type")
            if var_type == "number" or var_type == "integer" or var_type == "array":
                output_data.update({key: array([nan])})
            elif var_type == "string":
                output_data.update({key: array(["ERROR"])})
            else:
                msg = (
                    f"In the output JSON of the POST component, the key {key} has "
                    f"an unexpected type: {var_type}"
                )
                raise TypeError(msg)

        return output_data

    def _resample_curve_outputs(
        self, output_data: dict[str, ndarray]
    ) -> dict[str, ndarray]:
        """Resample all curve outputs specified in _OUTPUTS_TO_RESAMPLE into a new size
        of _RESAMPLING_OUTPUT_SIZE.

        Args:
            output_data: dict containing the curves to resample
        Returns:
            output_data: modified dict with resampled curves
        """

        for output_name in output_data.keys() - tuple(self._OUTPUTS_TO_RESAMPLE):
            if len(output_data[output_name]) not in [1, self._RESAMPLING_OUTPUT_SIZE]:
                LOGGER.warning(
                    f"The output {output_name} of size "
                    f"{len(output_data[output_name])} is not resampled to "
                    f"{self._RESAMPLING_OUTPUT_SIZE}."
                )

        # all y curves to be re-sampled are interpolated with a fictive x curve:
        x_new = linspace(0.0, 1.0, self._RESAMPLING_OUTPUT_SIZE)
        for curve in self._OUTPUTS_TO_RESAMPLE:
            y_old = output_data[curve]
            x_old = linspace(0.0, 1.0, len(y_old))
            output_data[curve] = interp(x_new, x_old, y_old)  # y_new

        return output_data
