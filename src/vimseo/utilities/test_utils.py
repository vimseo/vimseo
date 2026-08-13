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
import sys
from typing import TYPE_CHECKING

import pytest

from vimseo.api import create_model
from vimseo.core.base_integrated_model import IntegratedModelSettings
from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.base_storage_manager import PersistencyPolicy

if TYPE_CHECKING:
    from collections.abc import Mapping

    from gemseo.typing import StrKeyMapping
    from numpy import ndarray

    from vimseo.core.base_integrated_model import BaseIntegratedModel

LOGGER = logging.getLogger(__name__)


def check_model_outputs(
    model_name: str,
    load_case_name: str,
    input_data: StrKeyMapping,
    expected_outputs: Mapping[str, ndarray | str],
    relative_tolerance: float,
    *,
    directory_scratch_persistency: PersistencyPolicy = PersistencyPolicy.DELETE_NEVER,
    directory_archive_persistency: PersistencyPolicy = PersistencyPolicy.DELETE_NEVER,
    options: Mapping | None = None,
) -> BaseIntegratedModel:
    """Create a model, execute it, and check some of its outputs against expected values.

    Args:
        model_name: The name of the model.
        load_case_name: The name of the load case.
        input_data: A dictionary mapping input names to their values.
        expected_outputs: A dictionary mapping output names to their expected value (
            for equality assertion with computed outputs). The expected value may be
            an input name. In this case, the computed output value is compared to the
            value of this input name.
        relative_tolerance: The acceptable relative error for the outputs equality
            assertions.
        directory_scratch_persistency: The persistency policy of the scratch directory.
        directory_archive_persistency: The persistency policy of the archive directory.
        options: The extra options passed to :func:`.create_model`.

    Returns:
        The executed model, for callers that need to run further checks on it.
    """
    if options is None:
        options = {}

    model = create_model(
        model_name,
        load_case_name,
        model_options=IntegratedModelSettings(
            check_subprocess=True,
            directory_scratch_persistency=directory_scratch_persistency,
            directory_archive_persistency=directory_archive_persistency,
        ),
        **options,
    )
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    model.execute(input_data)
    # Saved before the assertions below so a diagnostic plot is still produced
    # when an expected-output check fails.
    model.plot_results(
        save=True, show=False, directory_path=model._archive_manager.job_directory
    )

    for output_name, expected_output in expected_outputs.items():
        # Instead of directly specifying the expected output value, it is possible
        #   to prescribe an input data name. The expected output beomes the value
        #   corresponding to this input data.
        if (
            type(expected_output) is str
            and expected_output in model.get_input_data_names()
        ):
            expected_output = model.get_input_data()[expected_output]

        computed_output = model.get_output_data()[output_name]

        assert computed_output == pytest.approx(
            expected_output, rel=relative_tolerance
        ), (
            (
                f"{output_name} : {computed_output} /= {expected_output} +- "
                f"{relative_tolerance * expected_output}"
            )
            if type(expected_output) is not str
            else " "
        )

    assert model.get_output_data()[MetaDataNames.error_code][0] == 0

    return model


def get_working_mock_command():
    """A command that works on Windows or Linux."""
    if sys.platform.startswith("win"):
        return "powershell Start-Sleep -m 50"
    return "sleep 0.05"


class SetConfig:
    def __init__(self, config, field_name, new_value):
        self._config = config
        self._field_name = field_name
        self._new_value = new_value
        self._original_value = None

    def __enter__(self):
        self._original_value = getattr(self._config, self._field_name)
        setattr(self._config, self._field_name, self._new_value)
        LOGGER.info(
            f"Replacing config field {self._config} with value {self._original_value} "
            f"by {self._new_value}."
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        LOGGER.info(
            f"Replacing back config value to {self._field_name}={self._original_value}."
        )
        setattr(self._config, self._field_name, self._original_value)
