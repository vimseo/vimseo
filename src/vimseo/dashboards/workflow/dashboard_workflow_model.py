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

import json
import tempfile
from copy import deepcopy
from dataclasses import asdict
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import get_type_hints

import streamlit as st
from gemseo import generate_coupling_graph
from pydantic import BaseModel
from streamlit_pydantic import pydantic_input

from vimseo.analysis_nodes.analysis_nodes_factory import AnalysisNodesFactory
from vimseo.analysis_nodes.analysis_nodes_factory import CompositeAnalysisNodesFactory
from vimseo.analysis_nodes.base_result import BaseResult
from vimseo.analysis_nodes.io.reader_analysis_nodes_factory import (
    ReaderAnalysisNodesFactory,
)
from vimseo.utilities.user import get_user_name
from vimseo.workflow.workflow_step import Input
from vimseo.workflow.workflow_step import WorkflowStep
from vimseo.workflow.workflow_step import get_pydantic_model_item

WORKFLOW_DATA_DIR = "workflow_data"


def initialize(session_state):

    working_directory = Path.cwd() / WORKFLOW_DATA_DIR
    if not working_directory.exists():
        working_directory.mkdir(parents=True)

    variables = {
        "analysis_node": None,
        "created_inputs": {},
        "created_outputs": {},
        "inputs": {},
        "outputs": {},
        "steps": {},
        "analysis_node_settings": {},
        "table_to_show": None,
        "workflow_name": "",
    }

    for name, default in variables.items():
        if name not in session_state:
            session_state[name] = default

    return working_directory


def update_analysis_node(session_state, analysis_node, settings):
    session_state.analysis_node = analysis_node
    session_state.analysis_node.update_options(**settings)
    session_state.analysis_node_settings = settings


def filter_settings(settings, settings_names):
    """Filtering, because streamlit pydantic appends all the settings when the pydantic
    model changes."""

    return {name: option for name, option in settings.items() if name in settings_names}


def add_unhandled_settings(analysis_node, settings):
    """Add the settings that are not handled by Streamlit-pydantic."""
    # TODO should be done in workflow step (method to_dict(settings_names)).
    model = analysis_node._st_settings
    if model is not None:
        default_settings = model().model_dump()
        missing_attrs = set(default_settings.keys()) - set(settings.keys())
        for attr in missing_attrs:
            # Handle the case where a settings field is a Pydantic model:
            if isinstance(model.model_fields[attr].default, BaseModel):
                sub_settings = pydantic_input(
                    key=attr,
                    model=model.model_fields[attr].default,
                    group_optional_fields="sidebar",
                    lowercase_labels=True,
                )
                settings[attr] = sub_settings
                settings[attr].update(
                    get_pydantic_model_item(model.model_fields[attr].default)
                )
            else:
                # Otherwise use the settings default value
                settings[attr] = default_settings[attr]


def get_input_description(analysis_node, attr_name):
    if analysis_node._INPUTS:
        return (
            f"{analysis_node._INPUTS.model_fields[attr_name].description}; "
            f"type is {get_input_type(analysis_node, attr_name)}"
        )
    return ""


def get_output_description(analysis_node, attr_name):
    output_description = [
        str(field.metadata)
        for field in fields(analysis_node.result)
        if field.name == attr_name
    ]
    return output_description[0] if len(output_description) > 0 else ""


def get_input_type(analysis_node, attr_name):
    return get_type_hints(analysis_node._INPUTS)[attr_name]


def get_result_attr_names(analysis_node):
    attr_names = list(set(dir(analysis_node.result)) - set(dir(BaseResult)))
    attr_names.append("result")
    return attr_names


def add_step(session_state, name, analysis_node_name, constructor_options):
    # Add undefined inputs with a default name, such that they are accessible as
    # input of the workflow:
    undefined_keys = set(session_state.analysis_node.input_names) - {
        input_.option_key for input_ in st.session_state.inputs.values()
    }
    for key in undefined_keys:
        input_name = f"{name}_{key}"
        st.session_state.inputs[input_name] = Input(input_name, key)

    session_state.steps[name] = {
        "name": name,
        "analysis_node_name": analysis_node_name,
        "inputs": [asdict(input_) for input_ in session_state.inputs.values()],
        "outputs": [asdict(output) for output in session_state.outputs.values()],
        "analysis_node_settings": deepcopy(session_state.analysis_node_settings),
        "analysis_node_constructor_options": deepcopy(constructor_options),
    }
    session_state.inputs = {}
    session_state.outputs = {}
    session_state.analysis_node_settings = {}


def get_workflow_file_name(suffix):
    user = get_user_name()
    datetime_ = datetime.now().strftime("%Y-%m-%d_T%H-%M-%S")
    if suffix != "":
        suffix = f"_{suffix}"
    return f"{user}_{datetime_}_workflow{suffix}.json"


def get_analysis_node_names():
    analysis_node_list = CompositeAnalysisNodesFactory().class_names
    for analysis_node in [
        "BaseCompositeAnalysisNode",
        "MyBaseCompositeAnalysisNode",
        "BaseVerification",
    ]:
        analysis_node_list.remove(analysis_node)
    return analysis_node_list


def get_reader_analysis_node_names():
    analysis_node_list = ReaderAnalysisNodesFactory().class_names
    for analysis_node in [
        "BaseReaderFile",
    ]:
        analysis_node_list.remove(analysis_node)
    return analysis_node_list


@st.cache_data
def load_workflow(workflow_json):
    steps = {}
    created_outputs = {}
    created_inputs = {}
    for data in workflow_json:
        for settings in json.load(data):
            steps[settings["name"]] = settings

            analysis_node = AnalysisNodesFactory().create(
                settings["analysis_node_name"]
            )

            for input_ in settings["inputs"]:
                created_inputs.update({input_["name"]: input_["option_key"]})

            for output in settings["outputs"]:
                attr_type = (
                    type(getattr(analysis_node.result, output["attr_name"]))
                    if output["attr_name"] != "result"
                    else type(analysis_node.result)
                )
                created_outputs.update({output["name"]: attr_type})

    return steps, created_inputs, created_outputs


def show_graph(steps):
    temp_dir = tempfile.TemporaryDirectory()
    dir_path = Path(temp_dir.name)
    file_path = dir_path / "graph.png"
    generate_coupling_graph([
        WorkflowStep.from_serialized_settings(**step) for step in list(steps.values())
    ]).visualize(show=False, file_path=str(file_path))
    st.image(str(file_path))
    temp_dir.cleanup()
