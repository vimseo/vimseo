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

import os
from pathlib import Path

import streamlit as st

from vimseo.dashboards.visualisation.identity import IDENTITY_COLORS
from vimseo.dashboards.visualisation.identity import VISUALISATION_IDENTITY_PATH


def banner_display(color):
    """Displays the banner with the specified color.

    Args:
        color (str) : color of the banner
    Return:
        None
    """

    st.markdown(
        f"""
        <div style="width: 160%; height: 6px; overflow: hidden;
        background-color: {color};"></div>
        """,
        unsafe_allow_html=True,
    )


def generate_layout(main_title):
    """Generate the generic layout (logos, banner)."""
    cwd = Path.cwd()
    os.chdir(VISUALISATION_IDENTITY_PATH)
    st.set_page_config(
        layout="wide",
        page_title=main_title,
        page_icon="vims_logo_small.png",
    )
    st.image("vims_logo.png", width=200)
    banner_display(IDENTITY_COLORS["purple"])
    st.text("")
    st.sidebar.image("logo_IRT_Saint_Exupery_RVB.png", width=200)
    st.sidebar.title(main_title)
    # st.markdown(
    #     """
    #     <style>
    #         section[data-testid="stSidebar"] {
    #             width: 650px !important;
    #         }
    #         [data-testid=stSidebar] [data-testid=stImage]{
    #             text-align: center;
    #             display: block;
    #             margin-left: auto;
    #             margin-right: auto;
    #             width: 100%;
    #         }
    #     </style>
    #     """,
    #     unsafe_allow_html=True,
    # )
    os.chdir(str(cwd))
