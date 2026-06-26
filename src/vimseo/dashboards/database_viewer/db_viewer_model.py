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

import streamlit as st
from gemseo.datasets.io_dataset import IODataset
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from matplotlib import pyplot as plt

from vimseo.utilities.datasets import dataframe_to_dataset
from vimseo.utilities.plotting_utils import plot_curves


def initialize(session_state):

    variables = {
        "model_name": "BendingTestAnalytical",
        "lc_name": "Cantilever",
        "scalar_names": [],
        "experiment_name": "",
        "selected_rows": [],
        "uri": "",
    }

    for name, default in variables.items():
        if name not in session_state:
            session_state[name] = default


@st.cache_data
def visualize_scalars(visualized_names, selected_rows, df, input_names):
    df_to_visualize = df.iloc[selected_rows]
    df_to_visualize = df_to_visualize.loc[:, visualized_names]
    names_to_suffixed_names = {}
    for name in visualized_names:
        if name in input_names:
            names_to_suffixed_names[name] = f"{name}[{IODataset.INPUT_GROUP}][0]"
        else:
            names_to_suffixed_names[name] = f"{name}[{IODataset.OUTPUT_GROUP}][0]"
    df_to_visualize.rename(columns=names_to_suffixed_names, inplace=True)
    ds = dataframe_to_dataset(df_to_visualize)

    fig, axes = plt.subplots()
    scatter_matrix = ScatterMatrix(
        ds,
        variable_names=visualized_names,
        kde=False,
    )
    scatter_matrix.execute(
        save=False,
        show=False,
        file_format="png",
        fig=fig,
        ax=axes,
    )
    st.pyplot(fig)


@st.cache_data
def visualize_curves(selected_rows, _curves, id_, _aranged_result_0):
    for i in range(len(_aranged_result_0.curves)):
        curves_selected = [
            c[i] for name, c in _curves.items() if name in id_[selected_rows].values
        ]
        fig = plot_curves(
            curves_selected,
            show=False,
            save=False,
            labels=[str(id_ + 1) for id_ in selected_rows],
        )
        fig.update_layout(width=300)
        st.plotly_chart(fig, use_container_width=True)
