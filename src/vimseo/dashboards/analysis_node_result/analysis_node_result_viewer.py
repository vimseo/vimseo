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

"""The page exploring any analysis node result, with a view chosen by the class of the result.

A validation case has a specific view; the other results have the generic view of
their tables and figures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from vimseo.analysis_nodes.doe.doe_result import DOEResult
from vimseo.analysis_nodes.validation_case.validation_case_result import (
    ValidationCaseResult,
)
from vimseo.dashboards.validation.validation_case_dashboard import (
    render_validation_case,
)
from vimseo.dashboards.visualisation.result_loader import st_load_analysis_node_result
from vimseo.dashboards.visualisation.result_view import render_result
from vimseo.dashboards.visualisation.sidebar import generic_sidebar
from vimseo.dashboards.visualisation.sidebar import model_sidebar

if TYPE_CHECKING:
    from collections.abc import Mapping

MAX_LISTED_FAMILIES = 5
"""The maximum number of families listed along an input."""


def describe_families(families: Mapping[str, Mapping[str, list[int]]]) -> str:
    """Describe the families of samples of a DOE differing by a single input.

    Args:
        families: The families along each input, see ``DOEResult.get_families``.

    Returns:
        The description, in Markdown.
    """
    if not families:
        return (
            "No family of samples varying a single input: the inputs vary jointly, "
            "e.g. in a LHS, so no parametric study is drawn. See the scatter matrix."
        )

    lines = [
        (
            "Families of samples varying a single input, along which a parametric "
            "study is drawn (*Figure settings > Abscissa name*):"
        )
    ]
    for name, name_families in families.items():
        if list(name_families) == [""]:
            (samples,) = name_families.values()
            lines.append(
                f"- along `{name}`: 1 family of {len(samples)} samples, "
                "the only varying input"
            )
            continue
        listed = [
            f"{key} ({len(samples)} samples)"
            for key, samples in list(name_families.items())[:MAX_LISTED_FAMILIES]
        ]
        if len(name_families) > MAX_LISTED_FAMILIES:
            listed.append("...")
        lines.append(
            f"- along `{name}`: {len(name_families)} families, {', '.join(listed)}"
        )
    return "\n".join(lines)


def analysis_node_result_viewer() -> None:
    result = st_load_analysis_node_result("analysis_node_result_viewer")
    if result is None:
        st.info(
            "Load an analysis node result from the sidebar: upload a result file, "
            "select a run in a directory archive or give its URI."
        )
        return

    st.markdown(f"## {type(result).__name__}")
    generic_sidebar(result)
    if result.metadata.model is not None:
        try:
            model_sidebar("Model", result.metadata.model, "analysis_node_result_viewer")
        except Exception as error:  # ruff: ignore[blind-except]
            st.sidebar.warning(f"The model cannot be described: {error}")

    if isinstance(result, ValidationCaseResult):
        render_validation_case(result)
        return

    if isinstance(result, DOEResult):
        st.info(describe_families(result.get_families()))
    render_result(result, "analysis_node_result_viewer")
