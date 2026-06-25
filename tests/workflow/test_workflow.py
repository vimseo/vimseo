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

from vimseo.workflow import WORKFLOW_LIB_DIR
from vimseo.workflow.workflow import Workflow


def test_workflow_from_json(tmp_wd):
    """Check that a workflow can be instantiated from a json file."""
    # TODO Sebastien review faulty test : should you add error_code and cpu_time to
    #  the workflow described in
    #  vimseo/src/vimseo/workflow/sebastien.bocquet_2024-10-07_T08-31-01_Workflow.json

    workflow = Workflow.from_json_path(
        WORKFLOW_LIB_DIR / "space__model__sensitivity_workflow.json"
    )
    output_data = workflow.execute()
    assert set(output_data.keys()) == {"m1", "ps1", "sens1"}


def test_set_reader_dir_path(tmp_wd):
    """Check that the path to the directories containing the input data can be
    modified."""
    workflow = Workflow.from_json_path(
        WORKFLOW_LIB_DIR / "parameter_space_reader__model__sensitivity_workflow.json"
    )
    workflow._set_input_file_dir_path("foo")
    assert workflow.steps["ParameterSpaceReader"].tool_settings.directory_path == "foo"
