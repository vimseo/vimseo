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
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from vimseo.api import create_model
from vimseo.core.base_integrated_model import IntegratedModelSettings
from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.base_storage_manager import PersistencyPolicy

if TYPE_CHECKING:
    from collections.abc import Mapping
    from importlib.metadata import EntryPoint

    from gemseo.typing import StrKeyMapping
    from numpy import ndarray
    from streamlit.testing.v1 import AppTest

    from vimseo.analysis_nodes.base_result import BaseResult
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


def check_result_visualization(
    result: BaseResult, directory_path: str | Path, **options
) -> None:
    """Check that an analysis node result can be visualized after being loaded from a file.

    The result is written to an HDF5 file, loaded back without knowing its class,
    and its figures, tables and plot choices are compared with the ones of the
    original result. Each plot choice is checked to be a setting, and a figure is
    drawn from the first value it proposes.

    Args:
        result: The analysis node result.
        directory_path: The directory where the result and its figures are written.
        **options: The settings of the visualization.
    """
    from vimseo.analysis_nodes.analysis_node_results_factory import load_result_file

    directory_path = Path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)
    path = directory_path / "result.hdf5"
    result.to_hdf5(path)
    loaded_result = load_result_file(path)
    assert type(loaded_result) is type(result)

    figures = result.plot(**options)
    figure_directory = directory_path / "figures"
    loaded_figures = loaded_result.plot(
        directory_path=figure_directory, save=True, **options
    )
    assert figures
    assert set(loaded_figures) == set(figures)
    for key in loaded_figures:
        files = list(figure_directory.glob(f"{key}.*"))
        assert len(files) == 1, key
        assert files[0].stat().st_size > 0

    tables = result.to_dataframes()
    loaded_tables = loaded_result.to_dataframes()
    assert set(loaded_tables) == set(tables)
    for key, table in tables.items():
        assert loaded_tables[key].shape == table.shape, key

    choices = result.get_plot_choices()
    assert loaded_result.get_plot_choices() == choices
    settings_fields = result._PLOT_SETTINGS.model_fields
    for name, values in choices.items():
        assert name in settings_fields, name
        assert values, name
        value = values[0] if settings_fields[name].annotation is str else values[:1]
        assert loaded_result.plot(**{**options, name: value}), name


DASHBOARD_TIMEOUT = 300
"""The timeout of an execution of a dashboard in a test, in seconds."""


def get_dashboard_entry_points(distribution_name: str) -> list[EntryPoint]:
    """Return the commands launching the dashboards of a distribution.

    Args:
        distribution_name: The name of the distribution, e.g. ``"vimseo"``.

    Returns:
        The entry points of the ``dashboard_*`` commands, sorted by name.
    """
    from importlib.metadata import entry_points

    return sorted(
        (
            entry_point
            for entry_point in entry_points(group="console_scripts")
            if entry_point.name.startswith("dashboard_")
            and entry_point.dist is not None
            and entry_point.dist.name.replace("_", "-") == distribution_name
        ),
        key=lambda entry_point: entry_point.name,
    )


def get_dashboard_script(entry_point: EntryPoint) -> Path | None:
    """Return the script launched by a dashboard command, without launching it.

    The command is executed with ``runpy.run_module`` replaced by a spy recording the
    arguments of ``streamlit run``.

    Args:
        entry_point: The entry point of the command.

    Returns:
        The path to the script, or ``None`` if the command does not launch a
        Streamlit script.
    """
    import runpy
    from unittest import mock

    calls = []
    with (
        mock.patch.object(sys, "argv", list(sys.argv)),
        mock.patch.object(
            runpy, "run_module", side_effect=lambda *_, **__: calls.append(sys.argv[:])
        ),
    ):
        entry_point.load()()

    if not calls:
        return None
    program, command, script = calls[0][:3]
    if (program, command) != ("streamlit", "run"):
        msg = f"{entry_point.name} does not run a Streamlit script: {calls[0]}."
        raise ValueError(msg)
    return Path(script)


def run_dashboard(script: str | Path) -> AppTest:
    """Execute a dashboard script as Streamlit would, without a browser.

    Args:
        script: The path to the script.

    Returns:
        The executed application, whose widgets can be actioned and checked.
    """
    import matplotlib
    from streamlit.testing.v1 import AppTest

    # The figures are created without display.
    matplotlib.use("Agg")
    app = AppTest.from_file(str(script), default_timeout=DASHBOARD_TIMEOUT)
    app.run()
    return app
