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

import re
from typing import TYPE_CHECKING

import streamlit as st

from vimseo.api import create_model

if TYPE_CHECKING:
    from collections.abc import Mapping


def inputs_in_columns(
    variable_names,
    component,
    key_prefix,
    default_value: float | Mapping[str, float],
    nb_columns=5,
):
    """Generate a list of input components according to a list of names.

    The input components are placed in an array.

    Args:
        variable_names: A component is created for each name of this list.
        component: The Streamlit component, either a text_input or a number_input.
        key_prefix: The prefix applied to the key associated to the component,
            to ensure the key unique.
        default_value: The default value of the component. If passed  as a ``float``,
            the value is applied to all components. If passed as a dictionary, the
            value is applied to each component according to its name.
        nb_columns: The number of columns of the array of components.
    """
    input_values = {}
    cols = st.columns(nb_columns)
    nb_full_rows = int(len(variable_names) / nb_columns)
    for i_row in range(nb_full_rows):
        for j, name in enumerate(
            variable_names[nb_columns * i_row : nb_columns + nb_columns * i_row]
        ):
            with cols[j]:
                input_values[name] = component(
                    name,
                    value=(
                        default_value[name]
                        if isinstance(default_value, dict)
                        else default_value
                    ),
                    key=f"{key_prefix}_{name}_{i_row}",
                )
    for j, name in enumerate(
        variable_names[nb_columns * nb_full_rows : len(variable_names)]
    ):
        with cols[j]:
            input_values[name] = component(
                name,
                value=(
                    default_value[name]
                    if isinstance(default_value, dict)
                    else default_value
                ),
                key=f"{key_prefix}_{name}",
            )
    return input_values


@st.cache_data
def st_create_model(model_name, lc_name, **options):
    """A Streamlit cached data function to create a model."""
    return create_model(model_name, lc_name, **options)


def multiselect_with_all(
    key, default_values, in_sidebar=False, help_: str | None = None
):
    """A Streamlit container adding an ``All`` button to a multiselection."""
    with st.container():
        if in_sidebar:
            all_ = st.sidebar.checkbox("Select all variables", key=f"{key}_all")
            if all_:
                selected_values = st.sidebar.multiselect(
                    "Choose variable(s)",
                    default_values,
                    key=key,
                    default=default_values,
                    help=help_,
                )
            else:
                selected_values = st.sidebar.multiselect(
                    "Choose variable(s)",
                    default_values,
                    key=key,
                    help=help_,
                )
        else:
            all_ = st.checkbox("Select all variables", key=f"{key}_all")
            if all_:
                selected_values = st.multiselect(
                    "Choose variable(s)",
                    default_values,
                    key=key,
                    default=default_values,
                    help=help_,
                )
            else:
                selected_values = st.multiselect(
                    "Choose variable(s)",
                    default_values,
                    key=key,
                    help=help_,
                )
    return selected_values


def camel_case_to_snake_case(text: str):
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    return pattern.sub("_", text).lower()
