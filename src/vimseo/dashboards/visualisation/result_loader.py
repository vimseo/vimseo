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

"""A widget to load an analysis node result from a file, an archive or a URI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st
from strenum import StrEnum

from vimseo.dashboards.visualisation.utils import load_result
from vimseo.storage_management import ArchiveManager
from vimseo.storage_management.analysis_node_archive import open_analysis_node_archive
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    BaseAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.uri import (
    get_default_archive_manager,
)
from vimseo.storage_management.analysis_node_archive.uri import get_default_archive_root
from vimseo.storage_management.analysis_node_archive.uri import (
    load_analysis_node_result,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vimseo.analysis_nodes.base_result import BaseResult

_ALL_ANALYSIS_NODES = "All analysis nodes"


class ResultSource(StrEnum):
    """The sources of an analysis node result."""

    UPLOAD = "Upload a file"
    ARCHIVE = "Archive"
    URI = "URI"


@st.cache_resource(show_spinner="Loading the analysis node result...")
def _load_from_content(content: bytes, file_format: str) -> BaseResult:
    return load_result(content, file_format)


@st.cache_resource(show_spinner="Loading the analysis node result...")
def _load_from_uri(uri: str, archive_root: str) -> BaseResult:
    return load_analysis_node_result(uri, directory_archive_root=archive_root)


@st.cache_data(ttl=30, show_spinner=False)
def _search_analysis_node_runs(archive_manager: str, archive_root: str) -> list[dict]:
    """Return the summaries of the finished analysis node runs of an archive."""
    if not Path(archive_root).is_dir():
        return []
    return open_analysis_node_archive(
        archive_manager, archive_root
    ).search_analysis_node_runs(status=BaseAnalysisNodeArchive.STATUS_FINISHED)


def _describe_run(summary: dict) -> str:
    """Return a short description of an analysis node run."""
    model = summary.get("model") or {}
    model_text = (
        f" | {model.get('name', '')} {model.get('load_case', '')}" if model else ""
    )
    return (
        f"{summary.get('datetime', '')[:19]} | {summary['analysis_node_name']}{model_text} | "
        f"{summary['analysis_node_run_id'][:8]}"
    )


def _load_from_archive(
    key: str,
    result_classes: Sequence[str],
    container,
) -> BaseResult | None:
    """Select an analysis node run in an archive and load its result."""
    archive_managers = [manager.value for manager in ArchiveManager]
    default_manager = get_default_archive_manager()
    archive_manager = container.selectbox(
        "Archive backend",
        archive_managers,
        index=archive_managers.index(default_manager)
        if default_manager in archive_managers
        else 0,
        key=f"{key}_archive_manager",
    )
    archive_root = container.text_input(
        "Root directory of the archive",
        value=str(get_default_archive_root()),
        key=f"{key}_archive_root",
    )
    summaries = [
        summary
        for summary in _search_analysis_node_runs(archive_manager, archive_root)
        if not result_classes or summary.get("result_class") in result_classes
    ]
    if not summaries:
        container.info(f"No finished analysis node run in {archive_root}.")
        return None

    analysis_node_names = sorted({
        summary["analysis_node_name"] for summary in summaries
    })
    analysis_node_name = container.selectbox(
        "Analysis node",
        [_ALL_ANALYSIS_NODES, *analysis_node_names],
        key=f"{key}_analysis_node_name",
    )
    summaries = sorted(
        (
            summary
            for summary in summaries
            if analysis_node_name
            in {_ALL_ANALYSIS_NODES, summary["analysis_node_name"]}
        ),
        key=lambda summary: summary.get("datetime", ""),
        reverse=True,
    )
    summary = container.selectbox(
        "Analysis node run",
        summaries,
        format_func=_describe_run,
        key=f"{key}_analysis_node_run",
    )
    return _load_from_uri(summary["uri"], archive_root)


def st_load_analysis_node_result(
    key: str,
    result_classes: Sequence[str] = (),
    file_formats: Sequence[str] = ("hdf5",),
    container=st.sidebar,
) -> BaseResult | None:
    """Load an analysis node result from a file, a directory archive or a URI.

    Args:
        key: A prefix making the keys of the widgets unique.
        result_classes: The names of the classes of the results which can be loaded
            from an archive. If empty, all of them.
        file_formats: The formats of the files which can be uploaded.
        container: The Streamlit container of the widgets.

    Returns:
        The analysis node result, or ``None`` if no result is loaded.
    """
    source = container.radio(
        "Load an analysis node result from", list(ResultSource), key=f"{key}_source"
    )
    try:
        if source == ResultSource.UPLOAD:
            uploaded_file = container.file_uploader(
                "Analysis node result file",
                type=list(file_formats),
                key=f"{key}_uploader",
            )
            if uploaded_file is None:
                return None
            return _load_from_content(
                uploaded_file.getvalue(), Path(uploaded_file.name).suffix[1:]
            )

        if source == ResultSource.ARCHIVE:
            return _load_from_archive(key, result_classes, container)

        uri = container.text_input(
            "URI",
            help="The path to a result file, the path to the directory of an analysis node run, "
            "analysis-node-run:{analysis_node_run_id} or runs:/{mlflow_run_id}.",
            key=f"{key}_uri",
        )
        archive_root = container.text_input(
            "Root directory of the archive (for analysis-node-run: and runs:/)",
            value=str(get_default_archive_root()),
            key=f"{key}_uri_archive_root",
        )
        if not uri:
            return None
        return _load_from_uri(uri, archive_root)
    except (
        FileNotFoundError,
        KeyError,
        NotImplementedError,
        OSError,
        ValueError,
    ) as error:
        container.error(f"The analysis node result cannot be loaded: {error}")
        return None
