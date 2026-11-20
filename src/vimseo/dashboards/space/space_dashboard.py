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

"""A dashboard to visualize results from a parameter space."""

from __future__ import annotations

import getpass
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime

import pandas as pd
import streamlit as st

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.lib.space_builder_factory import SpaceBuilderFactory
from vimseo.analysis_nodes.lib.space_builders import SpaceBuilder
from vimseo.analysis_nodes.space.random_variable_interface import distribution_to_dict
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.api import get_available_load_cases
from vimseo.api import get_available_models
from vimseo.dashboards.space.space_dashboard_model import get_default_bounds
from vimseo.dashboards.space.space_dashboard_model import get_space_builder_names
from vimseo.dashboards.space.space_dashboard_model import initialize
from vimseo.dashboards.space.space_dashboard_model import (
    load_parameter_space_from_file_or_material,
)
from vimseo.dashboards.space.space_dashboard_model import plot_distributions
from vimseo.dashboards.visualisation.result_loader import st_load_analysis_node_result
from vimseo.dashboards.visualisation.result_view import get_result_key
from vimseo.dashboards.visualisation.sidebar import write_default_inputs
from vimseo.dashboards.visualisation.utils import inputs_in_columns
from vimseo.dashboards.visualisation.utils import st_create_model
from vimseo.io.space_io import SpaceAnalysisNodeFileIO
from vimseo.utilities.list_utils import rotate_list


def space_dashboard():
    # Inject custom CSS to set the width of the sidebar
    # st.markdown(
    #     """
    #     <style>
    #         section[data-testid="stSidebar"] {
    #             width: 400px !important; # Set the width to your desired value
    #         }
    #     </style>
    #     """,
    #     unsafe_allow_html=True,
    # )

    initialize(st.session_state)

    # 1. The files defining the initial parameter space.
    st.sidebar.write("Load initial parameter space:")
    space_result = st_load_analysis_node_result(
        "space_result",
        result_classes=("SpaceAnalysisNodeResult",),
        file_formats=BaseAnalysisNode._RESULT_FORMATS,
    )
    material_json_file = st.sidebar.file_uploader(
        "Upload a material JSON file", type="json", key="space_material"
    )

    # 2. The model.
    st.sidebar.selectbox("Choose a model", get_available_models(), key="model_name")
    st.sidebar.selectbox(
        "Choose a load case",
        get_available_load_cases(st.session_state.model_name),
        key="lc_name",
    )
    model = st_create_model(st.session_state.model_name, st.session_state.lc_name)

    # 3. The initial parameter space, and the variables of the space to build.
    is_from_model_material = st.sidebar.checkbox("From model material", False)
    loaded_parameter_space = load_parameter_space_from_file_or_material(
        space_result,
        None if space_result is None else get_result_key(space_result),
        material_json_file,
        is_from_model_material,
        st.session_state.model_name,
        st.session_state.lc_name,
    )
    if st.sidebar.button("Set to initial parameter space"):
        st.session_state.space_analysis_node.result.parameter_space = (
            loaded_parameter_space
        )
    st.sidebar.multiselect(
        "variable_names", model.input_grammar.names, key="variable_names"
    )

    # 4. The settings of the loaded parameter space.
    st.sidebar.markdown("Initial parameter space:")
    st.sidebar.write(loaded_parameter_space.variable_names)
    if space_result is not None:
        with st.sidebar.expander("Settings of the loaded space analysis node"):
            st.json(asdict(space_result.metadata), expanded=True)

    # 5. The description of the model.
    st.sidebar.markdown("Model default inputs:")
    write_default_inputs(model.description.default_inputs)

    bounds = deepcopy(model.input_space)
    for name, value in bounds.items():
        value.append(model.default_input_data[name].shape[0])
    st.sidebar.markdown("Model bounds:")
    df = pd.DataFrame.from_dict(bounds, "index", columns=["lower", "upper", "length"])
    st.sidebar.dataframe(df)

    space_analysis_node = SpaceAnalysisNode()
    space_builders = get_space_builder_names()
    space_builders = rotate_list(space_builders, "FromModelMinAndMax")
    space_builders = rotate_list(space_builders, "FromModelCenterAndCov")
    st.selectbox(
        "Space builder name",
        space_builders,
        key="space_builder_name",
    )
    with st.form("distribution"):
        st.selectbox(
            "Distribution name",
            SpaceBuilderFactory()
            .create(st.session_state.space_builder_name)
            .get_available_distributions(),
            key="distribution_name",
        )

        space_settings = deepcopy(space_analysis_node.options)
        del space_settings["model"]

        if st.session_state.space_builder_name == "FromModelCenterAndCov":
            space_settings["variable_names"] = st.session_state.variable_names
            space_settings["cov"] = st.number_input("cov", value=0.05)
            space_settings["use_default_values_as_center"] = st.checkbox(
                "Use model default values as center",
                value=space_analysis_node.options["use_default_values_as_center"],
            )
            st.write(
                "Use only if ``Use model default values as center`` is not selected."
            )
            space_settings["center_value_expr"] = st.text_input(
                "Center value expression",
                value=SpaceBuilder.DEFAULT_CENTER_EXPRESSION,
            )
            space_settings["truncate_to_model_bounds"] = st.checkbox(
                "Truncate distributions to model bounds",
                value=space_analysis_node.options["truncate_to_model_bounds"],
            )

        elif st.session_state.space_builder_name == "FromCenterAndCov":
            space_settings["cov"] = st.number_input("cov", value=0.05)
            st.write("Choose values of distribution centers:")
            space_settings["center_values"] = inputs_in_columns(
                st.session_state.variable_names,
                st.number_input,
                "center",
                {name: value[0] for name, value in model.default_input_data.items()},
            )
            st.write("Choose values of distribution lower bounds:")
            # TODO do not update the dict if the value is None.
            space_settings["lower_bounds"] = {
                name: None if value == "None" else float(value)
                for name, value in inputs_in_columns(
                    st.session_state.variable_names, st.text_input, "lb", "None"
                ).items()
            }
            st.write("Choose values of distribution upper bounds:")
            # TODO do not update the dict if the value is None.
            space_settings["upper_bounds"] = {
                name: None if value == "None" else float(value)
                for name, value in inputs_in_columns(
                    st.session_state.variable_names, st.text_input, "ub", "None"
                ).items()
            }

        elif st.session_state.space_builder_name == "FromModelMinAndMax":
            space_settings["variable_names"] = st.session_state.variable_names
            space_settings["use_default_values_as_center"] = st.checkbox(
                "Use model default values as center",
                value=space_analysis_node.options["use_default_values_as_center"],
            )
            space_settings["center_value_expr"] = st.text_input(
                "Center value expression"
            )

        elif st.session_state.space_builder_name == "FromMinAndMax":
            st.write("Choose values of distribution minimums:")
            space_settings["minimum_values"] = inputs_in_columns(
                st.session_state.variable_names,
                st.number_input,
                "min",
                get_default_bounds(model, model.lower_bounds, -1),
            )
            st.write("Choose values of distribution maximums:")
            space_settings["maximum_values"] = inputs_in_columns(
                st.session_state.variable_names,
                st.number_input,
                "max",
                get_default_bounds(model, model.upper_bounds, 1),
            )
        else:
            msg = "Wrong space builder."
            raise ValueError(msg)

        submitted_space = st.form_submit_button("Submit space parameters")
        if submitted_space:
            space_builder = SpaceBuilderFactory().create(
                st.session_state.space_builder_name
            )
            filtered_options = {
                name: value
                for name, value in space_settings.items()
                if name in space_builder.grammar_names
            }
            try:
                st.session_state.space_analysis_node.execute(
                    distribution_name=st.session_state.distribution_name,
                    space_builder_name=st.session_state.space_builder_name,
                    model=model,
                    **filtered_options,
                )
            except ValueError as error:
                # Including the validation errors of the distribution settings.
                st.error(f"The parameter space cannot be built: {error}")
            if (
                len(
                    st.session_state.space_analysis_node.result.parameter_space.variable_names
                )
                == 0
            ):
                st.warning("The parameter space is empty")

    parameter_space = st.session_state.space_analysis_node.result.parameter_space
    variable_names = [
        name
        for name in model.input_grammar.names
        if name in parameter_space.variable_names
    ]

    show_model_bounds = st.checkbox("Show model bounds", value=False)
    distribution_plots, distribution_parameters = st.columns([0.5, 0.5])
    plots = plot_distributions(
        parameter_space, variable_names, model, show_model_bounds
    )
    with distribution_plots:
        for i, variable_name in enumerate(variable_names):
            if len(plots[variable_name]) > 1:
                component = st.selectbox(
                    "Choose component to plot",
                    range(len(plots[variable_name])),
                    key=f"variable_component_{i}",
                )
                st.plotly_chart(
                    plots[variable_name][component], use_container_width=True
                )
            else:
                st.plotly_chart(plots[variable_name][0], use_container_width=True)

    with distribution_parameters:
        for variable_name in variable_names:
            st.markdown(f"Parameters of {variable_name}:")
            st.json(
                distribution_to_dict(
                    variable_name, parameter_space.distributions[variable_name]
                ),
                expanded=True,
            )

    file_stem = (
        f"SpaceAnalysisNodeResult_{getpass.getuser()}_"
        f"{datetime.now().strftime('%Y-%m-%d_T%H-%M-%S')}"
    )
    result = st.session_state.space_analysis_node.result
    hdf5_column, json_column = st.columns(2)
    with hdf5_column:
        st.download_button(
            "Download (HDF5)",
            result.to_hdf5_buffer().getvalue(),
            file_name=f"{file_stem}.hdf5",
            mime="application/x-hdf5",
            key="download_hdf5",
        )
    with json_column:
        st.download_button(
            "Download (JSON)",
            SpaceAnalysisNodeFileIO().write(result),
            file_name=f"{file_stem}.json",
            mime="application/json",
            key="download_json",
        )
