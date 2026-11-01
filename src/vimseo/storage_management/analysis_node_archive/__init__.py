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

"""The archives of the results of the analysis nodes."""

from __future__ import annotations

import logging
from pathlib import Path

from vimseo.storage_management import ArchiveManager
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    BaseAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    NullAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.directory_analysis_node_archive import (
    DirectoryAnalysisNodeArchive,
)
from vimseo.utilities.optional_dependencies import import_optional

LOGGER = logging.getLogger(__name__)

NO_ANALYSIS_NODE_ARCHIVE = "none"
"""The name of the archive manager which disables the archive of the analysis node results."""


def open_analysis_node_archive(
    name: str, directory_archive_root: Path | str, study_name: str = ""
) -> BaseAnalysisNodeArchive:
    """Open the archive manager of the results of the analysis nodes.

    The analysis node runs already archived under ``directory_archive_root`` are kept: they
    can be searched and read, whatever their study, and the new analysis node runs are added
    to the study ``study_name``. Opening the archive creates nothing.

    The names are the ones of the archive managers of the simulations (see
    :class:`.ArchiveManager`), plus ``"none"`` to disable the archive.

    Args:
        name: The name of the archive manager.
        directory_archive_root: The root directory of the archive.
        study_name: The study of the analysis node runs written through the archive manager.
            If empty, the one of the configuration.

    Returns:
        The archive manager of the analysis node results, to search the analysis node runs and read
        their results; it is not a result.

    Raises:
        ValueError: If ``name`` does not match any archive manager.
    """
    if name.lower() == NO_ANALYSIS_NODE_ARCHIVE:
        return NullAnalysisNodeArchive()

    if name == ArchiveManager.Directory:
        return DirectoryAnalysisNodeArchive(Path(directory_archive_root), study_name)

    if name == ArchiveManager.Mlflow:
        # mlflow is shipped by the ``mlflow`` extra: it is imported lazily.
        import_optional(
            "mlflow", "mlflow", feature="The MLflow archive of the analysis nodes"
        )
        from vimseo.storage_management.analysis_node_archive.mlflow_analysis_node_archive import (
            MlflowAnalysisNodeArchive,
        )

        return MlflowAnalysisNodeArchive(directory_archive_root, study_name)

    msg = (
        f"Unknown archive manager for the analysis node results: {name}. "
        f"Available ones: {sorted([*(m.value for m in ArchiveManager), NO_ANALYSIS_NODE_ARCHIVE])}."
    )
    raise ValueError(msg)
