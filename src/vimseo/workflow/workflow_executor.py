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
import tempfile
import zipfile
from argparse import ArgumentParser
from pathlib import Path

from vimseo.api import activate_logger
from vimseo.workflow.workflow import Workflow

LOGGER = logging.getLogger(__name__)

parser = ArgumentParser(
    prog="Workflow executor",
    description="Execute a workflow.",
)
parser.add_argument("json_file_path", type=str)
parser.add_argument(
    "-i",
    "--input_path",
    type=str,
    default="",
    help="A zip file containing the workflow input data.",
)


def workflow_executor(
    file_path: Path | str,
    input_path: Path | str = "",
):
    """Execute a workflow stored in a ``JSON`` file."""
    workflow = Workflow.from_json_path(file_path)
    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(input_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)
        workflow._set_input_file_dir_path(Path(tmp_dir) / "workflow_data")
        workflow.execute()
        LOGGER.info(f"Workflow results: {workflow._chain.get_output_data()}")


def main():
    activate_logger()
    arguments = vars(parser.parse_args())
    workflow_executor(
        arguments["json_file_path"],
        input_path=arguments["input_path"],
    )


if __name__ == "__main__":
    main()
