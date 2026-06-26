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

import glob
import logging
import re
import time
from pathlib import Path

LOGGER = logging.getLogger(__name__)

WAIT_FILE_TIMEOUT = 10


def wait_for_file(file_path: Path, timeout: float | None = None) -> None:
    """Wait for a file to appear.

    Args:
        file_path: The path to the file expected to appear.

    Raises:
        A ``FileNotFoundError`` if the file is not found after the timeout.
    """
    timeout = WAIT_FILE_TIMEOUT if timeout is None else timeout
    time_counter = 0
    while not (file_path).is_file():
        time.sleep(1)
        time_counter += 1
        if time_counter > timeout:
            msg = f"File {file_path} was not found after {timeout}s."
            LOGGER.error(msg)
            raise FileNotFoundError(msg)

    LOGGER.debug(f"File {file_path} was found after {time_counter}s.")


def load_results(parent_dir_path: str | Path, file_format="hdf5"):
    """Load results based on a parent directory.

    All paths to ``.pickle`` file extensions found in the subdirectories
    of the parent directory are returned.
    """
    pattern = Path(parent_dir_path) / "**" / f"*.{file_format}"

    result_paths = []
    for file in glob.glob(str(pattern), recursive=True):  # noqa: PTH207
        file_path = Path(file)
        if file_path.is_file():
            result_paths.append(file_path)

    return result_paths


def camel_case_to_snake_case(text: str):
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    return pattern.sub("_", text).lower()
