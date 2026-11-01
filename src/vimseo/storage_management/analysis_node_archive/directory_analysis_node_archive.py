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

"""An archive of the results of the analysis nodes in local directories."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    BaseAnalysisNodeArchive,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    create_summary,
)
from vimseo.storage_management.analysis_node_archive.base_analysis_node_archive import (
    summary_to_json,
)
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.storage_management.directory_storage import DirectoryArchive

if TYPE_CHECKING:
    from vimseo.analysis_nodes.base_result import BaseResult

LOGGER = logging.getLogger(__name__)


class DirectoryAnalysisNodeArchive(DirectoryArchive, BaseAnalysisNodeArchive):
    """An archive of the results of the analysis nodes in local directories.

    It reuses the directory management of :class:`.DirectoryArchive`, the archive of
    the simulations, which it derives from: the archive of an analysis node run is a job
    directory named after the ``analysis_node_run_id``, under the directory of its analysis node in its
    study::

        {root_directory}/{study}/analysis_nodes/{analysis_node_name}/{analysis_node_run_id}/
            {analysis_node_name}_result.hdf5           # the result, written by BaseResult.to_hdf5
            {analysis_node_name}_result_metadata.json  # a readable summary of the run

    The result file has the name given by :meth:`.BaseAnalysisNode.save_results`, so that it
    tells which analysis node it comes from wherever it is opened.

    The summary lets the runs be searched without opening any result, and holds the
    links to the simulations (``simulation_run_ids``) and to the other analysis node runs
    (``parent_analysis_node_run_id``, ``child_analysis_node_run_ids``). The simulations themselves are in
    the archive of their model. An analysis node run which is still running, or which was
    interrupted, has the status ``"RUNNING"``.

    Most of the methods inherited from :class:`.DirectoryArchive` are meant for the
    simulations, and are not used.
    """

    SUMMARY_SUFFIX = "_result_metadata.json"
    """The suffix of the name of the file of the summary, after the analysis node name."""

    ANALYSIS_NODES_DIRECTORY_NAME = "analysis_nodes"
    """The name of the directory, under the root, of the analysis node runs."""

    def __init__(self, root_directory: Path | str, study_name: str = ""):
        """Create an archive.

        Args:
            root_directory: The root directory of the archive.
            study_name: The study of the analysis node runs written through this archive.
                If empty, the one of the configuration.
        """
        super().__init__(
            PersistencyPolicy.DELETE_NEVER,
            self.ANALYSIS_NODES_DIRECTORY_NAME,
            "",
            root_directory=Path(root_directory),
            study_name=study_name,
        )
        self._analysis_node_name = ""
        self._parent_run_id = ""
        self._analysis_node_run_id = ""

    @property
    def _job_sub_path(self) -> Path:
        return Path(
            self._study_name,
            self.ANALYSIS_NODES_DIRECTORY_NAME,
            self._analysis_node_name,
        )

    def _glob_runs(self, pattern: str, study_name: str = "") -> list[Path]:
        """Return the paths of the analysis node runs matching a pattern, in some studies.

        Args:
            pattern: The pattern under the directory of the analysis node runs of a study.
            study_name: The study. If empty, all the studies.
        """
        return sorted(
            self._root_directory.glob(
                f"{study_name or '*'}/{self.ANALYSIS_NODES_DIRECTORY_NAME}/{pattern}"
            )
        )

    def start_analysis_node_run(
        self,
        analysis_node_name: str,
        analysis_node_run_id: str,
        parent_analysis_node_run_id: str = "",
    ) -> None:
        self._analysis_node_name = analysis_node_name
        self._analysis_node_run_id = analysis_node_run_id
        self._parent_run_id = parent_analysis_node_run_id
        self.set_run_name(analysis_node_run_id)
        self.create_job_directory()
        self._write_summary(self.STATUS_RUNNING)

    @staticmethod
    def get_result_file_name(analysis_node_name: str) -> str:
        """Return the name of the file of the result, in the directory of a run.

        Args:
            analysis_node_name: The name of the analysis node.
        """
        from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode

        return BaseAnalysisNode.get_result_file_name(analysis_node_name)

    @classmethod
    def get_summary_file_name(cls, analysis_node_name: str) -> str:
        """Return the name of the file of the summary, in the directory of a run.

        Args:
            analysis_node_name: The name of the analysis node.
        """
        return f"{analysis_node_name}{cls.SUMMARY_SUFFIX}"

    def publish_analysis_node_result(self, result: BaseResult) -> None:
        result.to_hdf5(
            self._job_directory / self.get_result_file_name(self._analysis_node_name)
        )
        self._write_summary(self.STATUS_FINISHED, result=result)

    def end_analysis_node_run(self, status: str, error: str = "") -> None:
        self._write_summary(status, error=error)

    def _write_summary(
        self, status: str, result: BaseResult | None = None, error: str = ""
    ) -> None:
        summary = create_summary(
            self._analysis_node_name,
            self._analysis_node_run_id,
            self._parent_run_id,
            status,
            result=result,
            error=error,
            study_name=self._study_name,
        )
        (
            self._job_directory / self.get_summary_file_name(self._analysis_node_name)
        ).write_text(summary_to_json(summary))

    def _find_run_directory(
        self, analysis_node_run_id: str, analysis_node_name: str = ""
    ) -> Path:
        directories = self._glob_runs(
            f"{analysis_node_name or '*'}/{analysis_node_run_id}"
        )
        if len(directories) == 0:
            msg = (
                f"No archived analysis node run {analysis_node_run_id}"
                f"{f' of analysis node {analysis_node_name}' if analysis_node_name else ''} "
                f"in {self._root_directory}."
            )
            raise KeyError(msg)
        return directories[0]

    def get_analysis_node_result(
        self, analysis_node_run_id: str, analysis_node_name: str = ""
    ) -> BaseResult:
        from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode

        directory = self._find_run_directory(analysis_node_run_id, analysis_node_name)
        # The directory of a run is in the directory of its analysis node.
        path = directory / self.get_result_file_name(directory.parent.name)
        if not path.is_file():
            msg = (
                f"The analysis node run {analysis_node_run_id} has no result: its status is "
                f"{self._read_summary(directory)['status']}."
            )
            raise KeyError(msg)
        return BaseAnalysisNode.load_results(path)

    @staticmethod
    def _read_summary(directory: Path) -> dict[str, object]:
        return json.loads(
            (
                directory
                / DirectoryAnalysisNodeArchive.get_summary_file_name(
                    directory.parent.name
                )
            ).read_text()
        )

    def search_analysis_node_runs(
        self, analysis_node_name: str = "", status: str = "", study_name: str = ""
    ) -> list[dict[str, object]]:
        summaries = []
        for path in self._glob_runs(
            f"{analysis_node_name or '*'}/*/*{self.SUMMARY_SUFFIX}", study_name
        ):
            summary = json.loads(path.read_text())
            if status == "" or summary["status"] == status:
                summaries.append({
                    **summary,
                    # The study is the directory above the analysis nodes directory.
                    "study_name": path.parents[3].name,
                    "directory": str(path.parent),
                    # The directory of the run is a URI of its result.
                    "uri": str(path.parent),
                })
        return summaries

    def find_analysis_node_runs_of_simulation(
        self, simulation_run_id: str
    ) -> list[str]:
        return [
            summary["analysis_node_run_id"]
            for summary in self.search_analysis_node_runs()
            if simulation_run_id in summary.get("simulation_run_ids", ())
        ]
