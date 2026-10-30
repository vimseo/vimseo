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
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

import matplotlib.pyplot as plt
from numpy import array
from numpy import interp
from numpy import linspace
from numpy import nan

from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.core.model_metadata import MetaDataNames

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from numpy import ndarray

    from vimseo.core.load_case import LoadCase
    from vimseo.material.material import Material

LOGGER = logging.getLogger(__name__)


class PostProcessor(ExternalSoftwareComponent):
    """Class defining library of components dedicated to post-processing.

    Subclasses implement :meth:`_postprocess`, and may override :meth:`_is_run_faulty`
    and :meth:`_can_postprocess`: :meth:`_run` then decides, from these hooks and
    :attr:`POSTPROCESS_DESPITE_FAULTY_RUN`, whether to postprocess or to return NaN
    outputs. Overriding :meth:`_run` bypasses this logic.
    """

    _OUTPUTS_TO_RESAMPLE: ClassVar[Iterable[str]] = []
    """List of names of curves outputs to be resampled into a specific size."""

    _RESAMPLING_OUTPUT_SIZE = 100
    """Number of points to have on resampled curves."""

    POSTPROCESS_DESPITE_FAULTY_RUN: ClassVar[bool] = False
    """Whether to still attempt postprocessing when the RUN stage reported an error.

    When False (default, legacy behavior), the postprocessor returns NaN outputs
    without attempting any real postprocessing as soon as :meth:`_is_run_faulty`
    reports an error. When True, :meth:`_postprocess` is still called, provided that
    :meth:`_can_postprocess` finds enough to work with in the job directory. This
    lets models opt in individually, so existing models can be migrated to the new
    behavior progressively.
    """

    def __init__(
        self,
        load_case: LoadCase | None = None,
        material_grammar_file: Path | str = "",
        material: Material | None = None,
        check_subprocess: bool = False,
    ) -> None:
        super().__init__(load_case, material_grammar_file, material, check_subprocess)
        self.forbid_extra_output_names = check_subprocess

        self._output_physical_var_names = set(self.output_grammar.names) - {
            MetaDataNames.error_code.value
        }

    def _run(self, input_data):
        if self._is_run_faulty(input_data) and not self.POSTPROCESS_DESPITE_FAULTY_RUN:
            return self._generate_failed_output_data()
        if not self._can_postprocess():
            return self._generate_failed_output_data()
        return self._postprocess(input_data)

    def _postprocess(self, input_data) -> dict[str, ndarray]:
        """Compute the output data from the RUN results.

        Called only when :meth:`_run` decided that postprocessing can be attempted,
        possibly after a faulty run (see :attr:`POSTPROCESS_DESPITE_FAULTY_RUN`), in
        which case :meth:`_is_run_faulty` tells the two situations apart.
        """
        raise NotImplementedError

    def _is_run_faulty(self, input_data) -> bool:
        """Whether the RUN stage reported an error.

        Base implementation reads the upstream error code, a positive one reporting an
        error. Subclasses may override this method when the RUN stage reports its errors
        otherwise.
        """
        return self._get_upstream_error_code(input_data) > 0

    def _can_postprocess(self) -> bool:
        """Whether the job directory contains what postprocessing needs (e.g. a
        result file).

        Checked whether the RUN stage succeeded or not. Base implementation assumes
        the run can be post-processed; solver-specific subclasses should override this
        method (e.g. checking for an ODB file for Abaqus).
        """
        return True

    def _plot_output_data(self, data, x_data, y_data, save_path, save, show, fig_id):
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

    def _generate_nan_outputs(self, existing_data: Mapping[str, ndarray] | None = None):
        """Generates dummy outputs for all outputs expected by the output grammar of this
        component, that are not already present in ``existing_data``.

        Args:
            existing_data: Output values already computed, keyed by output name. Keys
                present here are kept as-is. If None, every output-grammar key is filled.
        """

        jsondata = self.output_grammar.schema
        output_data = {}

        for key in jsondata["properties"]:
            if existing_data is not None and key in existing_data:
                output_data[key] = existing_data[key]
                continue

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

    def _generate_failed_output_data(self) -> dict[str, ndarray]:
        """Dummy NaN-filled, resampled output data with the error code set, used
        when postprocessing failed or could not be attempted at all.
        """
        output_data = self._generate_nan_outputs()
        output_data = self._resample_curve_outputs(output_data)
        output_data[MetaDataNames.error_code] = array([1])
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
