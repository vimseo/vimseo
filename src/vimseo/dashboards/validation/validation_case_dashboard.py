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

from typing import TYPE_CHECKING

import plotly.graph_objects as go
import streamlit as st
from numpy import zeros

from vimseo.analysis_nodes.post_analysis_nodes.distribution_comparison_plot import (
    DistributionComparison,
)
from vimseo.analysis_nodes.result_visualization import create_figure
from vimseo.dashboards.validation.validation_case_dashboard_model import (
    NominalDataAdder,
)
from vimseo.dashboards.validation.validation_case_dashboard_model import (
    nominal_space_adder,
)
from vimseo.dashboards.visualisation.result_view import get_result_key
from vimseo.dashboards.visualisation.result_view import plot
from vimseo.dashboards.visualisation.result_view import render_figure
from vimseo.dashboards.visualisation.result_view import render_tables
from vimseo.dashboards.visualisation.result_view import to_dataframes
from vimseo.utilities.datasets import GROUP_SEPARATORS
from vimseo.utilities.datasets import dataset_to_dataframe
from vimseo.utilities.list_utils import rotate_list

if TYPE_CHECKING:
    from vimseo.analysis_nodes.validation_case.validation_case_result import (
        ValidationCaseResult,
    )


def render_validation_case(result: ValidationCaseResult) -> None:
    """Display a validation case: its metrics, its figures, and the errors versus the
    nominal inputs, from which the validation points can be selected.

    Args:
        result: The result of the validation case.
    """
    result_key = get_result_key(result)
    tables = to_dataframes(result, result_key)
    render_tables(
        {name: tables[name] for name in ("integrated_metrics",) if name in tables},
        "validation_case",
    )

    metric_name = st.selectbox("Select a metric", list(result.integrated_metrics))
    output_name = st.selectbox(
        "Select an output", list(result.integrated_metrics[metric_name])
    )

    figs = plot(
        result,
        result_key,
        metric_names=(metric_name,),
        output_names=(output_name,),
    )
    plot_type = st.selectbox("Select of case validation plot", list(figs.keys()))
    render_figure(figs[plot_type], "validation_case_plot")

    nominal_data_df = dataset_to_dataframe(result.element_wise_metrics)

    st.selectbox(
        "Choose the type of relationships that will be added "
        "to the nominal input variables.",
        list(NominalDataAdder),
        key="nominal_data_adder",
    )
    added_names = nominal_space_adder(
        nominal_data_df,
        adder_name=st.session_state.nominal_data_adder,
        layups=(
            nominal_data_df["layup"]
            if st.session_state.nominal_data_adder == NominalDataAdder.LAYUP
            else ()
        ),
    )

    # plot validation error against inputs (2D color map)

    st.markdown("## Nominal inputs:")
    st.dataframe(nominal_data_df)

    # If nominal space adder is LAYUP, rotate the list of variable names to start
    #  by the variable after ``layup``.
    scatter_axis_names = list(nominal_data_df.columns.values)
    scatter_axis_names = (
        rotate_list(
            scatter_axis_names,
            added_names[0],
        )
        if st.session_state.nominal_data_adder == NominalDataAdder.LAYUP
        else nominal_data_df.columns.values
    )

    column_name = (
        f"{output_name}{GROUP_SEPARATORS[0]}{metric_name}{GROUP_SEPARATORS[1]}"
    )
    marker_dict_map = {
        "color": nominal_data_df[column_name],
        "colorbar": {"title": metric_name},
        "colorscale": "rainbow",
        "cmid": 0,
        "size": 15,
        "showscale": True,
    }

    if len(scatter_axis_names) < 2:
        st.warning(
            f"There should be at least two scalar variables "
            f"in the nominal inputs: {scatter_axis_names}. "
            f"Scatter plot of nominal inputs cannot be shown."
        )
    else:
        if "x_axis" not in st.session_state:
            st.session_state["x_axis"] = scatter_axis_names[0]

        if "y_axis" not in st.session_state:
            st.session_state["y_axis"] = scatter_axis_names[1]

        col1, col2 = st.columns(2)
        with col1:
            selected_input_0 = st.selectbox(
                "Select x-axis", scatter_axis_names, key="x_axis"
            )
        with col2:
            selected_input_1 = st.selectbox(
                "Select y-axis", scatter_axis_names, key="y_axis"
            )

        if selected_input_0 != "" and selected_input_1 != "":
            input_0 = nominal_data_df[selected_input_0]
            input_1 = nominal_data_df[selected_input_1]

            fig_map = go.Figure(
                data=go.Scatter(
                    x=input_0,
                    y=input_1,
                    mode="markers",
                    marker=marker_dict_map,
                    # customdata=array(data[metric]),
                    # hovertemplate="<b> Point prop<br>" + \
                    #         "validation metric: %{customdata: .2f}"
                )
            )

            fig_map.update_layout(
                xaxis_title=f"<b>{selected_input_0}</b>",
                yaxis_title=f"<b>{selected_input_1}</b>",
            )

            if "hovering_variable_name" not in st.session_state:
                st.session_state["hovering_variable_name"] = scatter_axis_names[-1]

            st.selectbox(
                "Choose a variable to display while hovering on the scatter plot",
                scatter_axis_names,
                key="hovering_variable_name",
            )
            fig_map.update_traces(
                text=[
                    f"{st.session_state.hovering_variable_name}: "
                    f"{val}<br>{metric_name}: {metric_val}"
                    for val, metric_val in zip(
                        nominal_data_df[st.session_state.hovering_variable_name],
                        nominal_data_df[column_name],
                        strict=False,
                    )
                ]
            )

            results = result.stochastic_point_results
            event_dict = st.plotly_chart(
                fig_map,
                use_container_width=True,
                key="scatter",
                on_select="rerun",
            )
            if event_dict["selection"]["points"] and len(results) > 0:
                st.markdown("### Visualization of the selected validation points:")
                x = zeros(len(event_dict["selection"]["points"]))
                y = zeros(len(event_dict["selection"]["points"]))
                for i, point in enumerate(event_dict["selection"]["points"]):
                    x[i] = point["x"][0] if isinstance(point["x"], list) else point["x"]
                    y[i] = point["y"][0] if isinstance(point["y"], list) else point["y"]
                x.flatten()
                y.flatten()
                for xi, yi in zip(x, y, strict=False):
                    id_row = nominal_data_df.index[
                        (nominal_data_df[st.session_state.x_axis] == xi)
                        & (nominal_data_df[st.session_state.y_axis] == yi)
                    ]
                    for i in list(id_row):
                        st.markdown(f"#### Point ({xi}, {yi}):")

                        result = results[i]

                        st.plotly_chart(
                            create_figure(
                                DistributionComparison,
                                result,
                                output_name,
                                "CDF",
                                show_type_b_uncertainties=True,
                            ),
                            use_container_width=True,
                        )

                        st.write("Nominal value:")
                        st.dataframe(nominal_data_df.iloc[[i], :])

                        if st.checkbox(
                            "Validation point details",
                            False,
                            key=f"Validation_point_details_{i}",
                        ):
                            st.text(str(result).replace("\\n", "  \n"))
