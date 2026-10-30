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

"""Load a model result or an analysis node result from a reference.

A result is identified by one of these references:

==========================  ========================================  ============
Reference                   Model result (simulation)                 Analysis node result
==========================  ========================================  ============
bare identifier             ``{run_id}``                              ``{analysis_node_run_id}``
identifier with a scheme    ``run:{run_id}``                          ``analysis-node-run:{analysis_node_run_id}``
path                        the job directory of a simulation         a result file, or the directory of an analysis node run
MLflow run                  ``runs:/{mlflow_run_id}``                 ``runs:/{mlflow_run_id}``
==========================  ========================================  ============

An identifier is searched in every study of the archive, whose manager and root
directory are given separately. A string without scheme is a bare identifier when it
does not exist as a path and holds only letters, digits, ``_`` and ``-``; otherwise it
is a path. ``runs:/`` is the identifier shown by the user interface of MLflow;
since the ``run_name`` of a simulation is its ``run_id``, ``run:{run_id}`` is the usual
reference.

A path and ``runs:/`` name either kind of result: each loader checks the kind first and
raises a ``ValueError`` naming the right function when the reference is of the other
kind. The schemes are resolved by functions registered in :data:`URI_RESOLVERS` (analysis node
results) and :data:`MODEL_URI_RESOLVERS` (model results), so that new archives can be
plugged in.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from vimseo.storage_management import run_kind
from vimseo.storage_management.analysis_node_archive.directory_analysis_node_archive import (
    DirectoryAnalysisNodeArchive,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from vimseo.analysis_nodes.base_result import BaseResult
    from vimseo.core.model_result import ModelResult
    from vimseo.storage_management.base_archive_storage import ModelDataType

RUN_SCHEME = "run"
"""The scheme of a simulation, identified by its ``run_id``."""

ANALYSIS_NODE_RUN_SCHEME = "analysis-node-run"
"""The scheme of an analysis node run, identified by its ``analysis_node_run_id``."""

MLFLOW_RUN_SCHEME = "runs"
"""The scheme of a run in MLflow."""

_RESULTS_JSON_FILE = "results.json"
"""The file of the results of a simulation in its job directory."""

_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
"""The pattern of a bare identifier: no path separator and no dot, unlike a file."""

_SCHEME_PATTERN = re.compile(r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]+):(?P<path>.*)$")
"""The pattern of a URI with a scheme.

A scheme has at least two characters, so that a Windows drive letter is a path.
"""


def get_default_archive_root() -> str | Path:
    """Return the root directory of the archive by default.

    It is the one used by the models and the analysis nodes: the ``local_uri`` of the database
    of the configuration, else ``default_archive/``.
    """
    from vimseo.config.global_configuration import _configuration as config
    from vimseo.storage_management.archive_settings import DEFAULT_ARCHIVE_ROOT

    return config.database.local_uri or DEFAULT_ARCHIVE_ROOT


def get_default_archive_manager() -> str:
    """Return the archive manager of the analysis node results to read from by default.

    It is the one used by the analysis nodes: the ``analysis_node_archive_manager`` of the
    configuration, else its ``run_archive_manager``. When the archive of the analysis node
    results is disabled (``none``), it is the ``run_archive_manager``: disabling the
    archive of the new analysis node runs does not prevent from reading the former ones.
    """
    from vimseo.config.global_configuration import _configuration as config
    from vimseo.storage_management.analysis_node_archive import NO_ANALYSIS_NODE_ARCHIVE

    manager = config.analysis_node_archive_manager
    if not manager or manager.lower() == NO_ANALYSIS_NODE_ARCHIVE:
        return config.run_archive_manager
    return manager


def guess_archive_manager(directory_archive_root: str | Path) -> str:
    """Return the manager of an archive from its content.

    Args:
        directory_archive_root: The root directory of the archive.

    Returns:
        ``"MlflowArchive"`` if it is a local MLflow database, whose default experiment
        is described by ``0/meta.yaml``, ``"DirectoryArchive"`` if the root directory
        holds a study directory, whatever the study, else the archive manager of the
        configuration (see :func:`get_default_archive_manager`).
    """
    from vimseo.storage_management import ArchiveManager

    root = Path(directory_archive_root)
    if (root / "0" / "meta.yaml").is_file():
        return ArchiveManager.Mlflow
    if (
        root / DirectoryAnalysisNodeArchive.ANALYSIS_NODES_DIRECTORY_NAME
    ).is_dir() or any(path.is_dir() for path in root.glob("*")):
        return ArchiveManager.Directory
    return get_default_archive_manager()


def _get_mlflow_run_kind(mlflow_run_id: str, directory_archive_root: str | Path) -> str:
    """Return the kind of an MLflow run, ``simulation`` or ``analysis_node_run``.

    Args:
        mlflow_run_id: The id of the MLflow run.
        directory_archive_root: The root directory of a local MLflow database.

    Raises:
        KeyError: If there is no such MLflow run.
    """
    from vimseo.utilities.optional_dependencies import import_optional

    import_optional("mlflow", "mlflow", feature="The runs:/ URIs")
    from mlflow.exceptions import MlflowException
    from mlflow.tracking import MlflowClient

    from vimseo.storage_management.mlflow_storage import get_tracking_uri

    uri = get_tracking_uri(directory_archive_root or get_default_archive_root())
    try:
        run = MlflowClient(tracking_uri=uri).get_run(mlflow_run_id)
    except MlflowException as error:
        msg = f"No MLflow run {mlflow_run_id} in {uri}."
        raise KeyError(msg) from error
    return run.data.tags.get(run_kind.KIND_TAG, "")


def _wrong_kind(reference: str | Path, kind: str, function_name: str) -> ValueError:
    """Return the error raised when a reference is of the other kind of result."""
    return ValueError(
        f"{reference} is the reference of a {kind}; use {function_name}() to load it."
    )


def _load_from_analysis_node_run_id(
    analysis_node_run_id: str, archive_manager: str, directory_archive_root: str | Path
) -> BaseResult:
    """Load an analysis node result from an analysis node run of an archive, whatever its study.

    Args:
        analysis_node_run_id: The unique identifier of the analysis node run.
        archive_manager: The manager of the archive.
            If empty, use :func:`guess_archive_manager`.
        directory_archive_root: The root directory of the archive.
            If empty, use :func:`get_default_archive_root`.
    """
    from vimseo.storage_management.analysis_node_archive import (
        open_analysis_node_archive,
    )

    directory_archive_root = directory_archive_root or get_default_archive_root()
    archive = open_analysis_node_archive(
        archive_manager or guess_archive_manager(directory_archive_root),
        directory_archive_root,
    )
    return archive.get_analysis_node_result(analysis_node_run_id.strip("/"))


def _load_from_mlflow_run(
    mlflow_run_id: str, archive_manager: str, directory_archive_root: str | Path
) -> BaseResult:
    """Load an analysis node result from an MLflow run of an :class:`.MlflowAnalysisNodeArchive`.

    Args:
        mlflow_run_id: The id of the MLflow run.
        archive_manager: Unused, the archive being an MLflow one.
        directory_archive_root: The root directory of a local MLflow database.
            If empty, use :func:`get_default_archive_root`.

    Raises:
        ValueError: If the MLflow run is a simulation.
    """
    from vimseo.storage_management import ArchiveManager
    from vimseo.storage_management.analysis_node_archive import (
        open_analysis_node_archive,
    )

    mlflow_run_id = mlflow_run_id.strip("/")
    if _get_mlflow_run_kind(mlflow_run_id, directory_archive_root) == (
        run_kind.SIMULATION
    ):
        msg = f"{MLFLOW_RUN_SCHEME}:/{mlflow_run_id}"
        raise _wrong_kind(msg, "simulation", "load_model_results")
    archive = open_analysis_node_archive(
        ArchiveManager.Mlflow, directory_archive_root or get_default_archive_root()
    )
    return archive.get_analysis_node_result_of_mlflow_run(mlflow_run_id)


URI_RESOLVERS: dict[str, Callable[[str, str, str | Path], BaseResult]] = {
    ANALYSIS_NODE_RUN_SCHEME: _load_from_analysis_node_run_id,
    MLFLOW_RUN_SCHEME: _load_from_mlflow_run,
}
"""The functions loading an analysis node result from the path of a URI, the manager and the
root directory of an archive, bound to the scheme of the URI."""


def _load_from_path(path: Path) -> BaseResult:
    """Load an analysis node result from a result file or the directory of an analysis node run.

    Args:
        path: The path to the result file or to the directory of the analysis node run.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the path is the job directory of a simulation.
    """
    from vimseo.analysis_nodes.analysis_node_results_factory import load_result_file

    if path.is_file():
        return load_result_file(path)

    if path.is_dir():
        if (path / _RESULTS_JSON_FILE).is_file():
            raise _wrong_kind(path, "simulation", "load_model_results")
        # The directory of an analysis node run is in the directory of its analysis node.
        result_path = path / DirectoryAnalysisNodeArchive.get_result_file_name(
            path.parent.name
        )
        if result_path.is_file():
            return load_result_file(result_path)
        msg = (
            f"The directory {path} does not contain the result file {result_path.name}."
        )
        raise FileNotFoundError(msg)

    msg = f"No analysis node result at {path}."
    raise FileNotFoundError(msg)


def _split_reference(reference: str | Path, bare_scheme: str) -> tuple[str, str]:
    """Return the scheme and the path of a reference.

    Args:
        reference: The reference.
        bare_scheme: The scheme of a bare identifier.

    Returns:
        The scheme, empty for a path, and the path.
    """
    if isinstance(reference, Path):
        return "", str(reference)
    match = _SCHEME_PATTERN.match(reference)
    if match is not None:
        return match.group("scheme"), match.group("path")
    if not Path(reference).exists() and _IDENTIFIER_PATTERN.fullmatch(reference):
        return bare_scheme, reference
    return "", reference


def load_analysis_node_result(
    reference: str | Path,
    *,
    archive_manager: str = "",
    directory_archive_root: str | Path = "",
) -> BaseResult:
    """Load an analysis node result from a reference, see :mod:`.uri`.

    Args:
        reference: The reference of the analysis node result.
        archive_manager: The manager of the archive, used by the identifiers,
            e.g. ``"MlflowArchive"``. If empty, guess it from the content of the root
            directory (see :func:`guess_archive_manager`).
        directory_archive_root: The root directory of the archive, used by the
            identifiers and ``runs:/``. If empty, use :func:`get_default_archive_root`.

    Returns:
        The analysis node result.

    Raises:
        ValueError: If the scheme is not supported, or the reference is the one of a
            simulation.
    """
    scheme, path = _split_reference(reference, ANALYSIS_NODE_RUN_SCHEME)
    if scheme == "":
        return _load_from_path(Path(path))

    if scheme == RUN_SCHEME:
        raise _wrong_kind(reference, "simulation", "load_model_results")

    if scheme not in URI_RESOLVERS:
        msg = (
            f"Unsupported scheme '{scheme}' in the URI {reference}. "
            f"Supported schemes are {sorted(URI_RESOLVERS)}, "
            "or a path to a result file or to the directory of an analysis node run."
        )
        raise ValueError(msg)

    return URI_RESOLVERS[scheme](path, archive_manager, directory_archive_root)


def _open_simulation_archive(archive_manager: str, directory_archive_root: str | Path):
    """Open an archive of the simulations to read it.

    Args:
        archive_manager: The manager of the archive.
            If empty, use :func:`guess_archive_manager`.
        directory_archive_root: The root directory of the archive.
            If empty, use :func:`get_default_archive_root`.
    """
    from vimseo.storage_management import get_archive_class
    from vimseo.storage_management.base_storage_manager import PersistencyPolicy

    directory_archive_root = directory_archive_root or get_default_archive_root()
    archive_class = get_archive_class(
        archive_manager or guess_archive_manager(directory_archive_root)
    )
    return archive_class(
        PersistencyPolicy.DELETE_NEVER,
        model_name="",
        load_case_name="",
        root_directory=Path(directory_archive_root),
    )


def _load_model_from_run_id(
    run_id: str, archive_manager: str, directory_archive_root: str | Path
) -> ModelDataType:
    """Load the data of a simulation from its ``run_id``, whatever its study.

    Args:
        run_id: The ``run_id`` of the simulation.
        archive_manager: The manager of the archive.
        directory_archive_root: The root directory of the archive.

    Raises:
        KeyError: If the simulation is not in the archive.
    """
    archive = _open_simulation_archive(archive_manager, directory_archive_root)
    (data,) = archive.get_results_by_run_id([run_id.strip("/")])
    return data


def _load_model_from_mlflow_run(
    mlflow_run_id: str, archive_manager: str, directory_archive_root: str | Path
) -> ModelDataType:
    """Load the data of a simulation from its MLflow run.

    Args:
        mlflow_run_id: The id of the MLflow run.
        archive_manager: Unused, the archive being an MLflow one.
        directory_archive_root: The root directory of a local MLflow database.

    Raises:
        ValueError: If the MLflow run is an analysis node run.
    """
    from vimseo.storage_management import ArchiveManager

    mlflow_run_id = mlflow_run_id.strip("/")
    if (
        _get_mlflow_run_kind(mlflow_run_id, directory_archive_root)
        == run_kind.ANALYSIS_NODE_RUN
    ):
        msg = f"{MLFLOW_RUN_SCHEME}:/{mlflow_run_id}"
        raise _wrong_kind(msg, "analysis_node run", "load_analysis_node_results")
    archive = _open_simulation_archive(ArchiveManager.Mlflow, directory_archive_root)
    return archive.get_result(mlflow_run_id)


MODEL_URI_RESOLVERS: dict[str, Callable[[str, str, str | Path], ModelDataType]] = {
    RUN_SCHEME: _load_model_from_run_id,
    MLFLOW_RUN_SCHEME: _load_model_from_mlflow_run,
}
"""The functions loading the data of a simulation from the path of a URI, the manager
and the root directory of an archive, bound to the scheme of the URI."""


def _load_model_from_path(path: Path) -> ModelDataType:
    """Load the data of a simulation from its job directory.

    Raises:
        FileNotFoundError: If the path is not a job directory.
        ValueError: If the path is an analysis node run or an analysis node result file.
    """
    from vimseo.storage_management.base_storage_manager import PersistencyPolicy
    from vimseo.storage_management.directory_storage import DirectoryArchive

    if (path / _RESULTS_JSON_FILE).is_file():
        archive = DirectoryArchive(PersistencyPolicy.DELETE_NEVER, "", "")
        return archive.get_result(path)
    if path.is_file() or (path.is_dir() and any(path.glob("*_result.hdf5"))):
        raise _wrong_kind(path, "analysis_node result", "load_analysis_node_results")
    msg = f"No simulation at {path}: it is not a job directory."
    raise FileNotFoundError(msg)


def load_model_data(
    reference: str | Path,
    *,
    archive_manager: str = "",
    directory_archive_root: str | Path = "",
) -> ModelDataType:
    """Load the raw data of a simulation from a reference, see :mod:`.uri`.

    Args:
        reference: The reference of the simulation.
        archive_manager: The manager of the archive of the simulations, used by the
            identifiers. If empty, guess it from the content of the root directory.
        directory_archive_root: The root directory of the archive, used by the
            identifiers and ``runs:/``. If empty, use :func:`get_default_archive_root`.

    Returns:
        The inputs and the outputs of the simulation, the metadata being outputs.

    Raises:
        ValueError: If the scheme is not supported, or the reference is the one of a
            analysis node run.
    """
    scheme, path = _split_reference(reference, RUN_SCHEME)
    if scheme == "":
        return _load_model_from_path(Path(path))

    if scheme == ANALYSIS_NODE_RUN_SCHEME:
        raise _wrong_kind(reference, "analysis_node run", "load_analysis_node_results")

    if scheme not in MODEL_URI_RESOLVERS:
        msg = (
            f"Unsupported scheme '{scheme}' in the URI {reference}. "
            f"Supported schemes are {sorted(MODEL_URI_RESOLVERS)}, "
            "or the path to the job directory of a simulation."
        )
        raise ValueError(msg)

    return MODEL_URI_RESOLVERS[scheme](path, archive_manager, directory_archive_root)


def load_model_result(
    reference: str | Path,
    *,
    archive_manager: str = "",
    directory_archive_root: str | Path = "",
) -> ModelResult:
    """Load a model result from a reference, see :mod:`.uri`.

    The model of the simulation is not executed, but its class must be installed.

    Args:
        reference: The reference of the simulation.
        archive_manager: The manager of the archive of the simulations, used by the
            identifiers. If empty, guess it from the content of the root directory.
        directory_archive_root: The root directory of the archive, used by the
            identifiers and ``runs:/``. If empty, use :func:`get_default_archive_root`.

    Returns:
        The model result.

    Raises:
        ValueError: If the scheme is not supported, or the reference is the one of a
            analysis node run.
    """
    from vimseo.core.model_result import ModelResult

    return ModelResult.from_dict(
        load_model_data(
            reference,
            archive_manager=archive_manager,
            directory_archive_root=directory_archive_root,
        )
    )
