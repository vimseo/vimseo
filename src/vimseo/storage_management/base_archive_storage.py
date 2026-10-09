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

from abc import abstractmethod
from collections.abc import Mapping
from numbers import Number
from typing import TYPE_CHECKING

from gemseo.core.discipline.discipline_data import DisciplineData
from numpy import ndarray

from vimseo.core.model_metadata import DEFAULT_METADATA
from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.base_storage_manager import BaseStorageManager
from vimseo.utilities.model_data import decapsulate_length_one_array

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence
    from pathlib import Path

    from vimseo.storage_management.base_storage_manager import PersistencyPolicy

# TODO change to dataclasses
ModelDataType = Mapping[str, DisciplineData]
"""A dictionary with two items:
- 'inputs' to a dictionary mapping input variable names to arrays.
- 'outputs' to a dictionary mapping output variable names to arrays.
  Metadata are contained within this item.
"""

ArchiveResultType = Mapping[str, Mapping[str, ndarray | Number | str]]
"""A dictionary with the following items:
- 'inputs' to a dictionary mapping input variable names to an input data.
  If the data is a length-one array, the array item is directly considered.
- 'outputs' to a dictionary mapping output variable names to an output data.
  If the data is a length-one array, the array item is directly considered.
- 'metadata' to a dictionary mapping metadata variable names to the metadata value.
"""


def _order_results(
    run_ids: Sequence[str], found: Mapping[str, ModelDataType], location: object
) -> list[ModelDataType]:
    """Return the results found for some ``run_id``, in their order.

    Args:
        run_ids: The ``run_id`` of the simulations.
        found: The results found, bound to their ``run_id``.
        location: The location of the archive, for the error message.

    Raises:
        KeyError: If a simulation was not found.
    """
    missing = [run_id for run_id in run_ids if run_id not in found]
    if missing:
        msg = f"No simulation with run_id {missing} in the archive {location}."
        raise KeyError(msg)
    return [found[run_id] for run_id in run_ids]


class BaseArchiveManager(BaseStorageManager):
    """A base class for result database storage."""

    _persistent_file_names: list[str]

    def __init__(
        self,
        persistency: PersistencyPolicy,
        job_name: str = "",
        persistent_file_names: Iterable[str] = (),
    ):
        super().__init__(persistency)
        self._job_name = job_name
        self._persistent_file_names = persistent_file_names
        self._experiment_name = ""
        self._current_run_id = ""

    def add_persistent_file_names(self, persistent_file_names: Iterable[str]):
        self._persistent_file_names += persistent_file_names

    @property
    def persistent_file_names(self):
        """The names of the files that will be copied to the archive directory."""
        return self._persistent_file_names

    @property
    def uri(self) -> str:
        """The database root directory."""
        return str(self._root_directory)

    @property
    def root_directory(self) -> str:
        return ""

    @property
    def experiment_name(self):
        """The name of the current experiment."""
        return self._experiment_name

    @property
    def run_name(self):
        """The name of the current run."""
        return self._job_name

    def _prepare_archive_result(self, data: ModelDataType) -> ArchiveResultType:
        output_data = data["outputs"].copy()  # avoid mutable issues
        meta_data = {
            k: output_data[k] for k in output_data if k in DEFAULT_METADATA
        }  # extract meta_data from output_data
        for k in meta_data:  # remove metadata from outputs
            output_data.pop(k)
        input_data = data["inputs"]
        for k in input_data:  # remove inputs from outputs
            output_data.pop(k, None)
        return {
            "inputs": decapsulate_length_one_array(input_data),
            "outputs": decapsulate_length_one_array(output_data),
            "metadata": decapsulate_length_one_array(meta_data),
        }

    def enforce_persistency_policy(self, model_result: ModelDataType):
        """Create and feed archive with new job results, if informed policy is to be
        persistent."""

        archive_result = self._prepare_archive_result(model_result)

        if self.whether_to_delete(archive_result["metadata"][MetaDataNames.error_code]):
            self.delete_job_directory()
            return

        self.publish(archive_result)

    @abstractmethod
    def publish(self, archive_result: ArchiveResultType) -> None:
        """Publish a result."""

    @abstractmethod
    def get_result(self, archive_id: str | Path) -> ModelDataType:
        """Get an archived result."""

    @abstractmethod
    def get_results_by_run_id(self, run_ids: Iterable[str]) -> list[ModelDataType]:
        """Return the archived results of simulations from their ``run_id``.

        The ``run_id`` of a simulation is a metadata of its result. It is also the
        identifier listed in the ``simulation_run_ids`` of the metadata of a tool
        result. The whole archive is searched, whatever the experiment.

        Args:
            run_ids: The ``run_id`` of the simulations.

        Returns:
            The results, in the order of ``run_ids``.

        Raises:
            KeyError: If a simulation is not in the archive.
        """

    def abort_job(self):
        """Release what :meth:`create_job_directory` allocated, after a job failure.

        Called when the job raised before its results could be published. Does
        nothing by default: the job directory of a directory archive is left as is.
        """

    def set_experiment(self, experiment_name: str):
        """Set an experiment."""

    def set_run_name(self, run_name: str):
        """Set the run name."""
        self._job_name = run_name
