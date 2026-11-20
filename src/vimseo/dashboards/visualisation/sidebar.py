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

from dataclasses import asdict

import pandas as pd
import streamlit as st
from numpy import array

from vimseo.api import create_model
from vimseo.core.base_integrated_model import IntegratedModel

sidebar = st.sidebar


def write_default_inputs(default_inputs):
    group_names = [name.value for name in IntegratedModel.InputGroupNames]
    for group_name in group_names:
        data = {}
        for key, value in default_inputs[group_name].items():
            if array(value).size == 1:
                data.update({key: value[0]})
            else:
                data.update({key: str(value)})
        df = pd.DataFrame.from_dict(data, "index")
        sidebar.write(group_name)
        sidebar.write(df.sort_index())


def model_sidebar(title, model_description, key):

    sidebar.markdown(f"### {title}")
    sidebar.write("Name:", model_description.name)

    sidebar.write("Load case:", asdict(model_description.load_case))

    model = create_model(model_description.name, model_description.load_case.name)
    if model.image_path:
        sidebar.image(model.image_path)

    if model_description.summary:
        sidebar.write("Summary:", model_description.summary)

    component = sidebar.selectbox(
        "Component I/O",
        ["No selection", *list(model_description.dataflow.keys())],
        key=key + "component_selector",
    )
    if component != "No selection":
        sidebar.write(model_description.dataflow[component])

    sidebar.write("Default inputs")

    write_default_inputs(model_description.default_inputs)


# TODO rename
def generic_sidebar(result):
    sidebar.write("Vims version: ", result.metadata.generic["version"])
    sidebar.write("Analysis node settings:")
    try:
        st.sidebar.write(result.metadata.settings)
    except AttributeError:
        st.sidebar.write(result.metadata.analysis_node_options)
