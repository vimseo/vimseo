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

import matplotlib
import streamlit as st
from pandas import DataFrame

from vimseo.api import get_available_load_cases
from vimseo.api import get_available_models
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_result import ModelResult
from vimseo.dashboards.database_viewer.db_viewer_model import initialize
from vimseo.dashboards.database_viewer.db_viewer_model import visualize_curves
from vimseo.dashboards.database_viewer.db_viewer_model import visualize_scalars
from vimseo.dashboards.visualisation.generic_layout import generate_layout
from vimseo.dashboards.visualisation.utils import st_create_model

matplotlib.use("agg")


def db_viewer():

    initialize(st.session_state)

    st.sidebar.selectbox("Choose a model", get_available_models(), key="model_name")
    st.sidebar.selectbox(
        "Choose a load case",
        get_available_load_cases(st.session_state.model_name),
        key="lc_name",
    )

    st.sidebar.text_input(
        "Choose database URI",
        key="uri",
    )
    if st.session_state.uri != "":
        model = st_create_model(
            st.session_state.model_name,
            st.session_state.lc_name,
            directory_archive_root=st.session_state.uri,
        )
    else:
        model = st_create_model(st.session_state.model_name, st.session_state.lc_name)
    input_names = model.get_input_data_names()

    st.write(f"Database URI: {model.archive_manager.uri}")

    st.sidebar.text_input(
        "Choose an experiment",
        key="experiment_name",
    )

    if st.session_state.experiment_name != "":
        model.archive_manager.set_experiment(st.session_state.experiment_name)
        results = model.archive_manager.get_archived_results()

        aranged_result_0 = ModelResult.from_data(results[0], model=model)
        del aranged_result_0.metadata.report["directory_archive_job"]

        if st.button("Set default variables for exploration"):
            st.session_state.scalar_names = [
                MetaDataNames.date,
                MetaDataNames.model,
                MetaDataNames.load_case,
                MetaDataNames.error_code,
                MetaDataNames.cpu_time,
            ]
        st.multiselect(
            "Choose variables to explore",
            list(aranged_result_0.scalars.keys())
            + list(aranged_result_0.metadata.report.keys()),
            key="scalar_names",
        )
        if len(st.session_state.scalar_names) > 0:
            scalars = []
            curves = {}
            for r in results:
                aranged_result = ModelResult.from_data(r, model=model)
                aranged_result.scalars.update(aranged_result.metadata.report)
                # Add the unique ID from the result to scalars to identify the different runs
                aranged_result.scalars["ID"] = r["ID"]
                scalars.append(aranged_result.scalars)
                # Store curves in dict with the key being the unique ID
                curves[r["ID"]] = aranged_result.curves

            df = DataFrame(scalars)
            id_ = df["ID"]
            # Select only the columns corresponding to the chosen scalar variables and add the ID column at the end
            df_selected_vars = df.loc[:, st.session_state.scalar_names]
            df_selected_vars.insert(len(df_selected_vars.columns), "ID", id_)

            # Display the dataframe with the selected scalar variables and the ID column, and allow the user to select rows
            event = st.dataframe(
                df_selected_vars,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row",
            )
            st.session_state.selected_rows = event.selection.rows

            if len(st.session_state.selected_rows) > 0:
                col1, col2 = st.columns(2)
                with col1:
                    visualized_names = st.multiselect(
                        "Choose scalar variables to visualize",
                        aranged_result_0.get_numeric_scalars(),
                    )
                    if len(visualized_names) > 0:
                        visualize_scalars(
                            visualized_names,
                            st.session_state.selected_rows,
                            df,
                            input_names,
                        )

                with col2:
                    visualize_curves(
                        st.session_state.selected_rows, curves, id_, aranged_result_0
                    )


if __name__ == "__main__":
    generate_layout("Explore the simulation database")
    db_viewer()
