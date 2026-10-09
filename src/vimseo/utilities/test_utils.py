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

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint

    from streamlit.testing.v1 import AppTest

    from vimseo.tools.base_result import BaseResult

LOGGER = logging.getLogger(__name__)


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
    """Check that a tool result can be visualized after being loaded from a file.

    The result is written to an HDF5 file, loaded back without knowing its class,
    and its figures and tables are compared with the ones of the original result.

    Args:
        result: The tool result.
        directory_path: The directory where the result and its figures are written.
        **options: The settings of the visualization.
    """
    from vimseo.tools.tool_results_factory import load_result_file

    directory_path = Path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)
    path = directory_path / "result.hdf5"
    result.to_hdf5(path)
    loaded_result = load_result_file(path)
    assert type(loaded_result) is type(result)

    figures = result.visualize(**options)
    figure_directory = directory_path / "figures"
    loaded_figures = loaded_result.visualize(
        directory_path=figure_directory, save=True, **options
    )
    assert figures
    assert set(loaded_figures) == set(figures)
    for key in loaded_figures:
        files = list(figure_directory.glob(f"{key}.*"))
        assert len(files) == 1, key
        assert files[0].stat().st_size > 0

    tables = result.tabulate()
    loaded_tables = loaded_result.tabulate()
    assert set(loaded_tables) == set(tables)
    for key, table in tables.items():
        assert loaded_tables[key].shape == table.shape, key


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
