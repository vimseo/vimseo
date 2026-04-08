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

import getpass
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import streamlit as st
from streamlit_pydantic import pydantic_input

from vimseo.tools.io.reader_file_result import ResultFileReaderTool
from vimseo.tools.io.reader_tools_factory import ReaderToolsFactory
from vimseo.tools.lib.visualisation.generic_layout import generate_layout
from vimseo.tools.tools_factory import AnalysisToolsFactory
from vimseo.workflow.dashboard_workflow_model import WORKFLOW_DATA_DIR
from vimseo.workflow.dashboard_workflow_model import add_step
from vimseo.workflow.dashboard_workflow_model import add_unhandled_settings
from vimseo.workflow.dashboard_workflow_model import filter_settings
from vimseo.workflow.dashboard_workflow_model import get_analysis_tool_names
from vimseo.workflow.dashboard_workflow_model import get_input_description
from vimseo.workflow.dashboard_workflow_model import get_output_description
from vimseo.workflow.dashboard_workflow_model import get_reader_tool_names
from vimseo.workflow.dashboard_workflow_model import get_result_attr_names
from vimseo.workflow.dashboard_workflow_model import get_workflow_file_name
from vimseo.workflow.dashboard_workflow_model import initialize
from vimseo.workflow.dashboard_workflow_model import load_workflow
from vimseo.workflow.dashboard_workflow_model import show_graph
from vimseo.workflow.dashboard_workflow_model import update_tool
from vimseo.workflow.workflow_step import Input
from vimseo.workflow.workflow_step import Output


def workflow_dashboard():

    working_directory = initialize(st.session_state)

    workflow_json = st.sidebar.file_uploader(
        "Upload a workflow",
        type="json",
        key="workflow_uploader",
        accept_multiple_files=True,
    )
    if len(workflow_json) > 0 and st.sidebar.button("Upload workflow"):
        steps, created_inputs, created_outputs = load_workflow(workflow_json)
        st.session_state.steps.update(steps)
        st.session_state.created_outputs.update(created_outputs)
        st.session_state.created_inputs.update(created_inputs)

    if st.sidebar.button("Reset workflow"):
        st.session_state.steps = {}
        st.session_state.created_inputs = {}
        st.session_state.created_outputs = {}

    if st.sidebar.button("Clear loaded workflow cache"):
        st.cache_data.clear()

    st.text_input("Workflow name", key="workflow_name")

    if st.button("Update graph"):
        show_graph(st.session_state.steps)

    selection, visualization = st.columns((0.5, 0.5))

    with selection:
        tool_type = st.selectbox("Select a type of tool", ["Analysis", "Reader"])

        if tool_type == "Analysis":
            st.session_state.table_to_show = None
            tool_name = st.selectbox(
                "Select a tool",
                get_analysis_tool_names(),
            )
            with st.form("Create an analysis tool"):
                st.sidebar.markdown("### Current tool construction parameters")
                tmp_tool = AnalysisToolsFactory().create(tool_name)
                constructor_options = pydantic_input(
                    key="workflow_tool_constructor_options",
                    model=deepcopy(tmp_tool._STREAMLIT_CONSTRUCTOR_OPTIONS),
                    group_optional_fields="sidebar",
                    lowercase_labels=True,
                )

                tmp_tool = AnalysisToolsFactory().create(
                    tool_name, **constructor_options
                )
                st.sidebar.markdown("### Current tool settings")
                settings_model = deepcopy(tmp_tool._st_settings)
                if settings_model is not None:
                    settings = pydantic_input(
                        key="workflow_tool_options",
                        model=settings_model,
                        group_optional_fields="sidebar",
                        lowercase_labels=True,
                    )
                    settings = filter_settings(settings, tmp_tool.st_settings_names)
                    add_unhandled_settings(tmp_tool, settings)
                else:
                    settings = {}

                if st.form_submit_button("Submit tool"):
                    update_tool(st.session_state, tmp_tool, settings)
        else:
            tool_name = st.selectbox(
                "Select a tool",
                get_reader_tool_names(),
            )
            with st.form("Create a reader"):
                if tool_name == "ResultFileReaderTool":
                    tool_name_of_reader = st.selectbox(
                        "Select an analysis tool of which the result is to be read",
                        AnalysisToolsFactory().class_names,
                    )
                    tmp_tool = ResultFileReaderTool(tool_name_of_reader)
                    constructor_options = {"tool_name": tool_name_of_reader}
                else:
                    tmp_tool = ReaderToolsFactory().create(tool_name)
                    constructor_options = {}

                st.sidebar.markdown("### Current tool settings")
                settings_model = deepcopy(tmp_tool._st_settings)
                if settings_model is not None:
                    settings = pydantic_input(
                        key="workflow_tool_options",
                        model=settings_model,
                        group_optional_fields="sidebar",
                        lowercase_labels=True,
                    )
                else:
                    settings = {}

                if settings != {}:
                    settings = filter_settings(settings, tmp_tool.st_settings_names)

                result = st.file_uploader(
                    f"Select a {tmp_tool.get_file_extension()} file",
                    type=tmp_tool.get_file_extension(),
                )
                if result is not None:
                    # Update tool settings from information that can only be knows after
                    # reading the file.
                    file_path = working_directory / result.name
                    Path(file_path).write_bytes(result.getvalue())
                    settings["file_name"] = result.name
                    settings["directory_path"] = str(working_directory)

                if st.form_submit_button("Submit tool"):
                    update_tool(st.session_state, tmp_tool, settings)
                    if tmp_tool.get_file_extension() == ".csv":
                        st.session_state.table_to_show = tmp_tool.execute().dataset

        tool = st.session_state.tool
        if tool is not None:
            option_key = st.selectbox(
                "Tool input",
                tool.input_names,
            )
            with st.form("Add an input"):
                input_name = st.text_input(
                    "Input name", help=get_input_description(tool, option_key)
                )
                if st.form_submit_button("Submit input"):
                    if input_name == "":
                        msg = "An input name should be specified."
                        st.error(msg)
                        raise ValueError(msg)
                    # TODO use an ensemble instead of a dict?
                    st.session_state.created_inputs.update({
                        input_name: type(tool.options[option_key])
                    })
                    st.session_state.inputs[input_name] = Input(input_name, option_key)

            attr_names = get_result_attr_names(tool)
            attr_name = st.selectbox(
                "Result attribute",
                attr_names,
                help="Any attribute of the selected tool can be used as output. "
                "The result itself can also be used by selecting 'result'.",
            )

            with st.form("Add an output"):
                output_name = st.text_input(
                    "Output name", help=get_output_description(tool, attr_name)
                )
                if st.form_submit_button("Submit output"):
                    if output_name == "":
                        msg = "An output name should be specified."
                        st.error(msg)
                        raise ValueError(msg)
                    attr_type = (
                        type(getattr(tool.result, attr_name))
                        if attr_name != "result"
                        else type(tool.result)
                    )
                    st.session_state.created_outputs[output_name] = attr_type
                    st.session_state.outputs[output_name] = Output(
                        output_name, attr_name
                    )

            with st.form("Step definition"):
                name = st.text_input(
                    f"Override step name (default is {tool.name})",
                    value="",
                    key="workflow_step_name",
                )
                name = tool.name if name == "" else name
                submit_step = st.form_submit_button("Submit step")
                if submit_step:
                    if name in st.session_state.steps:
                        st.error(
                            f"The step name {name} exists in the already define steps"
                            f"({list(st.session_state.steps.keys())})."
                        )
                    else:
                        add_step(st.session_state, name, tool_name, constructor_options)

        if (
            st.checkbox("Modify step or inputs/outputs")
            and st.session_state.steps != {}
        ):
            with st.form("Delete steps"):
                step_names = st.multiselect(
                    "Select steps to delete",
                    list(st.session_state.steps.keys()),
                    key="workflow_select_delete_steps",
                )
                if st.form_submit_button("Submit deletion"):
                    for name in step_names:
                        del st.session_state.steps[name]

            with st.form("Delete inputs"):
                input_names = st.multiselect(
                    "Select inputs to delete",
                    list(st.session_state.inputs.keys()),
                    key="workflow_select_delete_inputs",
                )
                if st.form_submit_button("Submit deletion"):
                    for name in input_names:
                        del st.session_state.inputs[name]
                        del st.session_state.created_inputs[name]

            with st.form("Delete outputs"):
                output_names = st.multiselect(
                    "Select outputs to delete",
                    list(st.session_state.outputs.keys()),
                    key="workflow_select_delete_outputs",
                )
                if st.form_submit_button("Submit deletion"):
                    for name in output_names:
                        del st.session_state.outputs[name]
                        del st.session_state.created_outputs[name]

            with st.form("Modify step settings"):
                step_name = st.selectbox(
                    "Step to modify", list(st.session_state.steps.keys())
                )
                if st.form_submit_button("Submit modification"):
                    st.session_state.steps[step_name]["tool_settings"] = settings

        suffix = st.text_input("Suffix of workflow file name")
        file_name = get_workflow_file_name(suffix)
        st.write("Filename: ", file_name)
        st.download_button(
            "Download workflow",
            json.dumps(
                list(st.session_state.steps.values()),
                indent=4,
            ),
            file_name=file_name,
        )

        if st.button("Prepare input download"):
            # Download zip with input data
            user = getpass.getuser()
            datetime_ = datetime.now().strftime("%Y-%m-%d_T%H-%M-%S")
            if suffix != "":
                suffix = f"_{suffix}"
            input_zip_filename = f"inputs_{user}_{datetime_}_workflow{suffix}.zip"
            with ZipFile(input_zip_filename, "w") as myzip:
                for path in Path(WORKFLOW_DATA_DIR).glob("*"):
                    myzip.write(path)
            with Path(input_zip_filename).open("rb") as fp:
                st.download_button(
                    label="Download workflow inputs",
                    data=fp,
                    file_name=input_zip_filename,
                    on_click="ignore",
                    mime="application/zip",
                )

    with visualization:
        if st.session_state.table_to_show is not None:
            st.markdown("### Read csv data")
            st.table(st.session_state.table_to_show)

        if st.session_state.tool is not None:
            st.markdown("### Tool settings")
            st.write(st.session_state.tool_settings)

        st.markdown(f"### Current inputs for tool {tool_name}")
        st.write(st.session_state.inputs)

        st.markdown(f"### Current outputs for tool {tool_name}")
        st.write(st.session_state.outputs)

        st.markdown("### Created inputs")
        st.write(st.session_state.created_inputs)

        st.markdown("### Created outputs")
        st.write(st.session_state.created_outputs)

        st.markdown("### Steps")
        st.write(list(st.session_state.steps.values()))


if __name__ == "__main__":
    generate_layout("Workflow creation")
    workflow_dashboard()
