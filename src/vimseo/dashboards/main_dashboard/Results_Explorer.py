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

from vimseo.dashboards.visualisation.generic_layout import generate_layout

if __name__ == "__main__":
    generate_layout("Results")
    st.markdown(
        "Choose a page in the sidebar:\n"
        "- **Analysis Node Results**: explore any analysis node result, loaded from a file, an archive "
        "or a URI; a validation case has a specific view.\n"
        "- **Parameter Space**: build a parameter space, possibly from a loaded one.\n"
        "- **Model Results**: explore the model results of an archive, refined by "
        "study, model, load case, status or query."
    )
