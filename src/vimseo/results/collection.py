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

"""The collections of results: a set of model results or of analysis node results.

A collection is immutable: every verb returns a new collection or a new object
(``DataFrame``, :class:`.Families`, figures), and nothing is deleted from the archive.
It holds the table of the summaries of its results, one row per result, and loads a
result only when it is accessed (``results[i]``, iteration) or when its curves are
drawn. Each verb is a call of a function of :mod:`.operations`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Generic
from typing import TypeVar

from pandas import DataFrame

from vimseo.results import operations
from vimseo.results.operations import INPUT_PREFIX
from vimseo.results.operations import OUTPUT_PREFIX

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from vimseo.analysis_nodes.result_visualization import Figure

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")

MAX_SUPERPOSED_RESULTS = 20
"""The number of results above which superposing their curves is discouraged."""


class FamilyKey(Mapping):
    """The values of the inputs shared by a family of results, frozen and hashable."""

    def __init__(self, items: Iterable[tuple[str, Any]] = ()):
        self.__items = tuple(items)

    def __getitem__(self, name: str) -> Any:
        for key, value in self.__items:
            if key == name:
                return value
        raise KeyError(name)

    def __iter__(self) -> Iterator[str]:
        return iter(key for key, _ in self.__items)

    def __len__(self) -> int:
        return len(self.__items)

    def __hash__(self) -> int:
        return hash(self.__items)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FamilyKey):
            return self.__items == other.__items
        if isinstance(other, tuple):
            return self.__items == other
        return NotImplemented

    def __str__(self) -> str:
        return ", ".join(f"{key}={value}" for key, value in self.__items) or "all"

    def __repr__(self) -> str:
        return f"FamilyKey({self})"


class ResultsCollection(Generic[T]):
    """An immutable collection of results, model results or analysis node results."""

    _ID_COLUMN: ClassVar[str] = "run_id"
    """The column of the identifiers of the results."""

    _KIND: ClassVar[str] = "results"
    """The name of the results in the messages."""

    def __init__(
        self,
        summaries: DataFrame,
        loader: Callable[[Mapping[str, Any]], T],
        ignored: Iterable[str] = (),
        cache: dict[str, T] | None = None,
    ) -> None:
        """
        Args:
            summaries: The summaries of the results, one row per result.
            loader: The function loading a result from its summary.
            ignored: The names of the inputs ignored by the comparisons.
            cache: The results already loaded, bound to their identifiers.
        """
        self.__summaries = self._prune(summaries.reset_index(drop=True))
        self.__loader = loader
        self.__ignored = tuple(dict.fromkeys(ignored))
        self.__cache = {} if cache is None else cache

    def _new(self, summaries: DataFrame, ignored: Iterable[str] | None = None):
        """Return a collection of the same kind, sharing the loaded results."""
        return type(self)(
            summaries,
            self.__loader,
            self.__ignored if ignored is None else ignored,
            self.__cache,
        )

    @staticmethod
    def _prune(summaries: DataFrame) -> DataFrame:
        """Return the summaries without the columns foreign to the results.

        Args:
            summaries: The summaries of the results.
        """
        return summaries

    @property
    def summaries(self) -> DataFrame:
        """The summaries of the results, one row per result."""
        return self.__summaries.copy()

    @property
    def ignored(self) -> tuple[str, ...]:
        """The names of the inputs ignored by the comparisons."""
        return self.__ignored

    def _load(self, row: Mapping[str, Any]) -> T:
        """Return the result of a row of the summaries, loaded once."""
        identifier = row[self._ID_COLUMN]
        if identifier not in self.__cache:
            self.__cache[identifier] = self.__loader(row)
        return self.__cache[identifier]

    def __len__(self) -> int:
        return len(self.__summaries)

    def __iter__(self) -> Iterator[T]:
        for _, row in self.__summaries.iterrows():
            yield self._load(row)

    def __getitem__(self, index: int | slice):
        if isinstance(index, slice):
            return self._new(self.__summaries.iloc[index])
        return self._load(self.__summaries.iloc[index])

    def __repr__(self) -> str:
        summaries = self.__summaries
        text = f"{type(self).__name__}({len(self)} {self._KIND}"
        for column in ("study_name", self._NAME_COLUMN):
            if column in summaries.columns and not summaries.empty:
                text += f", {column} {sorted(summaries[column].astype(str).unique())}"
        if "status" in summaries.columns and not summaries.empty:
            text += f", status {summaries['status'].value_counts().to_dict()}"
        if self.__ignored:
            text += f", ignoring {list(self.__ignored)}"
        return f"{text})"

    _NAME_COLUMN: ClassVar[str] = "model_name"
    """The column of the names of the models or of the analysis nodes."""

    def filter(
        self, query: str = "", failed: bool | None = None, **metadata: Any
    ) -> ResultsCollection[T]:
        """Return the results matching every condition.

        Args:
            query: A query, see :mod:`.query`, e.g.
                ``"`inputs.mesh_size` < 0.5 or `outputs.max_force` > 1050"``.
            failed: Whether to keep only the failed results (``True``), only the
                others (``False``), or both (``None``). A result is failed when its
                status is not ``FINISHED`` or its ``error_code`` is positive.
            **metadata: Values of metadata, e.g. ``model_name="DebondingENF"``.

        Returns:
            A new collection.
        """
        return self._new(
            operations.filter_summaries(self.__summaries, query, failed, **metadata)
        )

    def ignoring(self, *names: str) -> ResultsCollection[T]:
        """Return the same results, ignoring some inputs in the comparisons.

        The ignored inputs are left out of :meth:`varying_inputs`, :meth:`families`
        and :meth:`duplicates`; they stay in the results and in :meth:`to_dataframe`.

        Args:
            *names: The names of the inputs.

        Returns:
            A new collection.
        """
        return self._new(self.__summaries, (*self.__ignored, *names))

    def _check_homogeneous(self) -> None:
        """Check that the results can be compared: nothing to check by default."""

    def varying_inputs(self) -> DataFrame:
        """Return the inputs taking several values, except the ignored ones.

        Returns:
            One row per varying input, with the number of its values and the values.
        """
        self._check_homogeneous()
        return operations.get_varying_inputs(self.__summaries, self.__ignored)

    def duplicates(self) -> DataFrame:
        """Return the groups of results with the same inputs; nothing is deleted.

        Returns:
            The results which have a duplicate, with a column ``group``.
        """
        self._check_homogeneous()
        return operations.find_duplicates(self.__summaries, self.__ignored)

    def to_dataframe(self, variable_names: Iterable[str] = ()) -> DataFrame:
        """Return the table of the results, one row per result.

        Args:
            variable_names: The names of the inputs and outputs. If empty, all the
                columns of the summaries.

        Returns:
            The table, indexed by the identifiers of the results.
        """
        return operations.to_dataframe(
            self.__summaries, self._ID_COLUMN, variable_names
        )

    def to_dataset(self, variable_names: Iterable[str] = ()):
        """Return the numerical inputs and outputs as an ``IODataset``.

        Args:
            variable_names: The names of the inputs and outputs. If empty, all the
                numerical ones.
        """
        return operations.to_dataset(self.__summaries, variable_names)

    def families(self, along: str) -> Families:
        """Group the results differing by a single input.

        Args:
            along: The name of the input varying in a family.

        Returns:
            The families, bound to the values of the other varying inputs.
        """
        self._check_homogeneous()
        families, ungrouped = operations.group_by_variation(
            self.__summaries, along, self.__ignored
        )
        if ungrouped:
            LOGGER.warning(
                f"{len(ungrouped)} {self._KIND} belong to no family (a single value of "
                f"{along}): "
                f"{list(self.__summaries.loc[ungrouped, self._ID_COLUMN])}."
            )
        return Families(
            {
                FamilyKey(key): self._new(self.__summaries.loc[rows])
                for key, rows in families.items()
            },
            along,
            self.__ignored,
            self._new(self.__summaries.loc[ungrouped]),
        )

    def visualize(self, **settings: Any) -> dict[str, Figure]:
        """Return the figures of the results."""
        raise NotImplementedError

    def _plot_family(self, along: str, title: str = "") -> dict[str, Figure]:
        """Return the figures of the results as a family varying along an input."""
        from vimseo.analysis_nodes.result_visualization import plot_family

        summaries = self.__summaries.sort_values(
            f"{INPUT_PREFIX}{along}", kind="stable"
        )
        return plot_family(
            self._get_curve_sets(summaries),
            list(summaries[f"{INPUT_PREFIX}{along}"]),
            [operations.get_scalars(row) for _, row in summaries.iterrows()],
            along,
            title,
        )

    def _get_curve_sets(self, summaries: DataFrame) -> list[dict[str, Any]]:
        """Return the curve sets of some results, bound to the names of the figures."""
        return [{} for _ in range(len(summaries))]


class ModelResults(ResultsCollection["ModelResult"]):
    """A collection of model results, the results of simulations."""

    _KIND = "model results"

    def visualize(self, plot_names: Iterable[str] = ()) -> dict[str, Figure]:
        """Superpose the curves of the results, one figure per plot of the model.

        Args:
            plot_names: The names of the figures. If empty, all the figures of the
                model.

        Returns:
            The figures, whose traces are labelled by the varying inputs. A figure
            missing from some results is not drawn, with a warning.
        """
        from vimseo.utilities.plotting_utils import superpose_curves

        if len(self) > MAX_SUPERPOSED_RESULTS:
            LOGGER.warning(
                f"Superposing the curves of {len(self)} results: use families(along=...) "
                "to group them."
            )
        results = list(self)
        if not results:
            return {}
        plot_names = list(plot_names) or list(
            dict.fromkeys(name for result in results for name in result.plots.names)
        )
        missing_names = [
            name
            for name in plot_names
            if not all(name in result.plots.names for result in results)
        ]
        if missing_names:
            LOGGER.warning(
                f"The figures {missing_names} are not drawn: some results do not "
                "have them."
            )
        labels = operations.get_labels(self.summaries, self._ID_COLUMN, self.ignored)
        return {
            name: superpose_curves(
                [result.plots[name] for result in results],
                labels=labels,
                save=False,
                show=False,
            )
            for name in plot_names
            if name not in missing_names
        }

    def _get_curve_sets(self, summaries: DataFrame) -> list[dict[str, Any]]:
        return [
            {curve_set.name: curve_set for curve_set in self._load(row).plots}
            for _, row in summaries.iterrows()
        ]

    def compare_to(
        self,
        reference: Mapping[str, float],
        output_names: Iterable[str] = (),
        weights: Mapping[str, float] | None = None,
    ) -> DataFrame:
        """Return the relative errors of the scalar outputs to reference values.

        Args:
            reference: The reference values of the outputs.
            output_names: The names of the outputs. If empty, those of ``reference``.
            weights: The weights of the outputs in the weighted sum of the errors.
                If ``None``, each output weighs 1.

        Returns:
            One row per result: the relative error of each output and their weighted
            sum, ``weighted_error``.
        """
        output_names = list(output_names) or list(reference)
        weights = weights or {}
        table = self.to_dataframe(output_names)
        errors = DataFrame(index=table.index)
        for name in output_names:
            errors[name] = (table[name] - reference[name]).abs() / abs(reference[name])
        errors["weighted_error"] = sum(
            weights.get(name, 1.0) * errors[name] for name in output_names
        )
        return errors

    def to_cache(self, path: str | Path):
        """Return an HDF5 cache of the simulations, e.g. to feed a model.

        Args:
            path: The path of the HDF5 file.

        Returns:
            The cache.
        """
        from gemseo.caches.hdf5_cache import HDF5Cache
        from numpy import atleast_1d

        cache = HDF5Cache(hdf_file_path=path, hdf_node_path="node")
        for result in self:
            data = result.archived_data
            cache.cache_outputs(
                {name: atleast_1d(value) for name, value in data["inputs"].items()},
                {name: atleast_1d(value) for name, value in data["outputs"].items()},
            )
        return cache


class AnalysisNodeResults(ResultsCollection["BaseResult"]):
    """A collection of analysis node results, the results of analysis node runs.

    The inputs of an analysis node run are its scalar settings and the identity of its model;
    its outputs are its key values (see :meth:`.BaseResult.get_key_values`). The
    collection of the results of a single analysis node has only the inputs and the outputs of
    this analysis node, not those of the other analysis nodes of the archive.
    """

    _ID_COLUMN = "analysis_node_run_id"
    _KIND = "analysis_node results"
    _NAME_COLUMN = "analysis_node_name"

    @staticmethod
    def _prune(summaries: DataFrame) -> DataFrame:
        # The summaries of an archive hold the inputs and outputs of all its analysis nodes,
        # missing for the runs of the other analysis nodes.
        if (
            "analysis_node_name" not in summaries.columns
            or summaries["analysis_node_name"].nunique() != 1
        ):
            return summaries
        foreign = [
            column
            for column in summaries.columns
            if column.startswith((INPUT_PREFIX, OUTPUT_PREFIX))
            and summaries[column].isna().all()
        ]
        return summaries.drop(columns=foreign)

    def _check_homogeneous(self) -> None:
        analysis_node_names = set(self.summaries.get("analysis_node_name", ()))
        if len(analysis_node_names) > 1:
            msg = (
                f"The analysis node results come from several analysis nodes, {sorted(analysis_node_names)}: "
                "select one with filter(analysis_node_name=...)."
            )
            raise ValueError(msg)

    def visualize(self) -> dict[str, Figure]:
        """Return the figures of the key values versus the varying setting.

        Returns:
            The figure of the key values versus the only varying setting, or no
            figure when several settings vary (use :meth:`families`).
        """
        varying = list(self.varying_inputs().index)
        if len(varying) != 1:
            LOGGER.warning(
                f"The analysis node results vary along {varying}: plot their families instead."
            )
            return {}
        return self._plot_family(varying[0])

    def children(self, analysis_node_run_id: str) -> AnalysisNodeResults:
        """Return the results of the sub-analysis nodes of an analysis node run.

        Args:
            analysis_node_run_id: The identifier of the analysis node run of the parent.
        """
        return self.filter(parent_analysis_node_run_id=analysis_node_run_id)

    def model_results(self, **archive: Any) -> ModelResults:
        """Return the model results of the simulations of the analysis node runs.

        Args:
            **archive: The archive settings of the simulations, see
                :func:`.load_model_results`.
        """
        from vimseo.api import load_model_results

        run_ids = list(
            dict.fromkeys(
                run_id
                for result in self
                for run_id in result.metadata.simulation_run_ids
            )
        )
        return load_model_results(run_ids, **archive)


class Families(Mapping):
    """The families of results differing by a single input.

    It maps the values of the other varying inputs (a :class:`.FamilyKey`) to the
    collection of a family, whose results are sorted by the varying input.
    """

    def __init__(
        self,
        families: Mapping[FamilyKey, ResultsCollection],
        along: str,
        ignoring: Iterable[str],
        ungrouped: ResultsCollection,
    ) -> None:
        """
        Args:
            families: The families, bound to their keys.
            along: The name of the input varying in a family.
            ignoring: The names of the inputs ignored by the comparisons.
            ungrouped: The results alone in their group.
        """
        self.__families = dict(families)
        self.along = along
        """The name of the input varying in a family."""
        self.ignoring = tuple(ignoring)
        """The names of the inputs ignored by the comparisons."""
        self.ungrouped = ungrouped
        """The results alone in their group."""

    def __getitem__(self, key: FamilyKey | tuple) -> ResultsCollection:
        return self.__families[key if isinstance(key, FamilyKey) else FamilyKey(key)]

    def __iter__(self) -> Iterator[FamilyKey]:
        return iter(self.__families)

    def __len__(self) -> int:
        return len(self.__families)

    def get(self, default: Any = None, **fixed: Any) -> ResultsCollection | Any:
        """Return the family of the given values of the other varying inputs.

        Args:
            default: The value returned when there is no such family.
            **fixed: The values of the other varying inputs, e.g.
                ``mesh_size_exterior=1.0``.
        """
        for key, family in self.__families.items():
            if dict(key) == fixed:
                return family
        return default

    def __repr__(self) -> str:
        lines = [
            (
                f"Families(along={self.along!r}, ignoring={self.ignoring}, "
                f"{len(self)} families, {len(self.ungrouped)} ungrouped)"
            )
        ]
        for key, family in self.__families.items():
            values = list(family.summaries[f"{INPUT_PREFIX}{self.along}"])
            lines.append(f"  {key}   {type(family).__name__}({len(family)}, {values})")
        if len(self.ungrouped):
            lines.append(f"  ungrouped   {list(self.ungrouped.summaries.iloc[:, 0])}")
        return "\n".join(lines)

    def visualize(self) -> dict[str, Figure]:
        """Return the figures of each family.

        Returns:
            For each family, the figure of its scalar outputs versus the varying input
            and the figures superposing its curves, labelled by the varying input;
            the keys end with the key of the family, e.g.
            ``curves_load_displacement[mesh_size_exterior=1.0]``.
        """
        figures = {}
        for key, family in self.__families.items():
            figures.update({
                f"{name}[{key}]": figure
                for name, figure in family._plot_family(self.along, str(key)).items()
            })
        return figures

    def to_dataframe(self) -> DataFrame:
        """Return the table of the results of the families, with a column ``family``."""
        tables = [
            family.to_dataframe().assign(family=str(key))
            for key, family in self.__families.items()
        ]
        return DataFrame() if not tables else _concat(tables)


def _concat(tables: list[DataFrame]) -> DataFrame:
    """Concatenate tables."""
    from pandas import concat

    return concat(tables)


def create_analysis_node_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Create the summary of an analysis node run for a collection, from its archived summary.

    Args:
        summary: The summary of the analysis node run, see :func:`.create_summary`.

    Returns:
        The identity of the analysis node run, its scalar settings as ``inputs.{name}`` and its
        key values as ``outputs.{name}``.
    """
    model = summary.get("model") or {}
    flat = {
        "analysis_node_run_id": summary.get("analysis_node_run_id", ""),
        "analysis_node_name": summary.get("analysis_node_name", ""),
        "study_name": summary.get("study_name", ""),
        "status": summary.get("status", ""),
        "datetime": summary.get("datetime", ""),
        "parent_analysis_node_run_id": summary.get("parent_analysis_node_run_id", ""),
        "result_class": summary.get("result_class", ""),
        "model_name": model.get("name", ""),
        "load_case": model.get("load_case", ""),
        "simulation_run_ids": list(summary.get("simulation_run_ids", ())),
        "uri": summary.get("uri", ""),
    }
    for name, value in (summary.get("settings") or {}).items():
        if isinstance(value, str):
            try:
                import json

                value = json.loads(value)
            except ValueError:
                pass
        if isinstance(value, (int, float, str)) and not isinstance(value, bool):
            flat[f"{INPUT_PREFIX}{name}"] = value
    for name, value in (summary.get("key_values") or {}).items():
        flat[f"{OUTPUT_PREFIX}{name}"] = value
    return flat
