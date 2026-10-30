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

import logging
from collections import UserDict
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from numbers import Number
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from gemseo.utils.string_tools import MultiLineString
from numpy import atleast_1d
from numpy import ndarray
from pandas import DataFrame

from vimseo.analysis_nodes.base_result import BaseResult
from vimseo.analysis_nodes.result_visualization import BasePlotSettings
from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.storage_management.directory_storage import DirectoryArchive
from vimseo.utilities.curves import CurveSet
from vimseo.utilities.curves import NamedList
from vimseo.utilities.fields import MeshField

if TYPE_CHECKING:
    from vimseo.analysis_nodes.result_visualization import Figure
    from vimseo.core.base_integrated_model import IntegratedModel
    from vimseo.storage_management.base_archive_storage import ModelDataType

LOGGER = logging.getLogger(__name__)

ScalarDataType = Mapping[str, float | int | str]

_GROUPS = ("all", "inputs", "outputs")
"""The groups of variables of a model result."""


class VariableMapping(UserDict):
    """The values of the variables of a model result, bound to their names.

    It is a dictionary, e.g. ``result.scalars["x"]``, which can also be called to
    select the variables by name, by type and by group, e.g.
    ``result.scalars(group="inputs")``.
    """

    input_names: tuple[str, ...]
    """The names of the input variables."""

    def __init__(self, data: Mapping[str, Any] = (), input_names: Iterable[str] = ()):
        """
        Args:
            data: The values of the variables.
            input_names: The names of the input variables.
        """
        super().__init__(data)
        self.input_names = tuple(input_names)

    def __call__(
        self,
        variable_names: Iterable[str] = (),
        numerical: bool = True,
        group: str = "all",
    ) -> dict[str, Any]:
        """Return some variables.

        Args:
            variable_names: The names of the variables. If empty, all of them.
            numerical: Whether to keep only the numbers.
            group: The group of the variables, ``"all"``, ``"inputs"`` or
                ``"outputs"``.

        Returns:
            The selected variables.

        Raises:
            ValueError: If the group is unknown.
        """
        if group not in _GROUPS:
            msg = f"Unknown group {group}; the groups are {list(_GROUPS)}."
            raise ValueError(msg)
        variable_names = list(variable_names)
        return {
            name: value
            for name, value in self.items()
            if (not variable_names or name in variable_names)
            and (not numerical or isinstance(value, Number) or _is_numerical(value))
            and (group == "all" or (group == "inputs") == (name in self.input_names))
        }


def _is_numerical(value: Any) -> bool:
    """Return whether a value is an array of numbers."""
    return isinstance(value, ndarray) and value.dtype.kind in "biufc"


class ModelResultPlotSettings(BasePlotSettings):
    """The settings of the figures of a model result."""

    plot_names: tuple[str, ...] = ()
    """The names of the figures, see :meth:`.Plot.get_name`. All of them if empty."""


@dataclass
class ModelResult(BaseResult):
    """The result of a simulation, in a user-friendly format.

    The scalars and the vectors are mappings which can be called to select variables,
    e.g. ``scalars(group="inputs")``. The curves and the figures are lists which can
    also be indexed by name, e.g. ``curves["dplt_vs_dplt_grid"]`` and
    ``plots["dplt_vs_dplt_grid"]``. :meth:`to_dict` gives back the raw dictionary the
    result was built from.
    """

    _PLOT_SETTINGS: ClassVar[type[ModelResultPlotSettings]] = ModelResultPlotSettings

    scalars: VariableMapping = field(default_factory=VariableMapping)
    """The scalar variables, inputs and outputs."""

    vectors: VariableMapping = field(default_factory=VariableMapping)
    """The vector variables which are not drawn by a curve, inputs and outputs."""

    curves: NamedList = field(default_factory=NamedList)
    """All the curves, flattened over the figures, named ``{y}_vs_{x}``.

    Use it to reach a curve regardless of the figure it belongs to, typically to
    compute a curve measure on it.
    """

    plots: NamedList = field(default_factory=NamedList)
    """The curves grouped by figure, named after their :class:`.Plot`.

    Each item is a :class:`.CurveSet` holding the curves of one figure and the
    :class:`.Plot` declaring how to draw them: abscissa, line styles, ordinate axes,
    reference lines and title. A figure can therefore be redrawn from the result
    alone, without the model that produced it.
    """

    fields: Mapping[str, Iterable[MeshField | Path | str]] = field(default_factory=dict)
    snapshots: Iterable[Path | str] = field(default_factory=list)

    input_names: tuple[str, ...] = ()
    """The names of the input variables."""

    archived_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    """The raw data the result was built from, see :meth:`to_dict`."""

    # TODO Add timestamp attr in Field, and fill this value based on a variable name
    #  representing time

    def __post_init__(self) -> None:
        self._wrap_fields()

    def _wrap_fields(self) -> None:
        """Give the fields their types, e.g. after a deserialization."""
        self.input_names = tuple(self.input_names)
        self.scalars = VariableMapping(self.scalars, self.input_names)
        self.vectors = VariableMapping(self.vectors, self.input_names)
        self.curves = NamedList(self.curves)
        self.plots = NamedList(self.plots)

    @classmethod
    def _from_hdf5_file(cls, f):
        result = super()._from_hdf5_file(f)
        result._wrap_fields()
        return result

    def _get_metadata(self, name: str) -> str:
        """Return a metadata of the simulation as a string, empty if absent."""
        value = self.metadata.report.get(name, "")
        return str(atleast_1d(value)[0]) if len(atleast_1d(value)) else ""

    @property
    def run_id(self) -> str:
        """The ``run_id`` of the simulation."""
        return self._get_metadata(MetaDataNames.run_id)

    @property
    def study_name(self) -> str:
        """The study of the simulation."""
        return self._get_metadata(MetaDataNames.study_name)

    @property
    def model_name(self) -> str:
        """The name of the model."""
        return self._get_metadata(MetaDataNames.model)

    @property
    def load_case(self) -> str:
        """The name of the load case."""
        return self._get_metadata(MetaDataNames.load_case)

    @property
    def status(self) -> str:
        """The status of the simulation, ``FINISHED`` when it is unknown."""
        return self._get_metadata(MetaDataNames.status) or "FINISHED"

    @property
    def analysis_node_run_id(self) -> str:
        """The ``analysis_node_run_id`` of the analysis node run which executed the simulation."""
        return self._get_metadata(MetaDataNames.analysis_node_run_id)

    @classmethod
    def from_dict(
        cls,
        model_data: ModelDataType | Mapping[str, Mapping[str, Any]],
        model: IntegratedModel | None = None,
        load_fields: bool = False,
    ) -> ModelResult:
        """Create a model result from raw model data.

        Args:
            model_data: The raw data: ``{"inputs", "outputs"}`` as stored in an
                archive (the metadata being outputs), or ``{"inputs", "outputs",
                "metadata"}`` as returned by :meth:`to_dict`.
            model: The model of the simulation, to know its figures.
                If ``None``, it is created from the metadata, so its class must be
                installed.
            load_fields: Whether to load the fields from their files.

        Returns:
            The model result.
        """
        model_data = {
            "inputs": dict(model_data["inputs"]),
            "outputs": {
                **model_data["outputs"],
                **{
                    name: atleast_1d(value)
                    for name, value in model_data.get("metadata", {}).items()
                },
            },
        }
        archive_manager = DirectoryArchive(
            PersistencyPolicy.DELETE_ALWAYS,
            "",
            "",
        )
        archive_result = archive_manager._prepare_archive_result(model_data)
        model = (
            model
            if model is not None
            else create_model(
                archive_result["metadata"]["model"],
                archive_result["metadata"]["load_case"],
            )
        )
        result = cls(input_names=tuple(archive_result["inputs"]))
        result.archived_data = {
            "inputs": dict(model_data["inputs"]),
            "outputs": dict(model_data["outputs"]),
        }
        result.metadata.model = model.description
        for name in MetaDataNames:
            if name in archive_result["metadata"]:
                result.metadata.report[name] = archive_result["metadata"][name]
        data = dict(archive_result["inputs"], **archive_result["outputs"])
        plotted_names = []
        for spec in model.plots:
            curve_set = CurveSet.from_data(spec, data)
            result.plots.append(curve_set)
            result.curves.extend(
                curve
                for curve in curve_set.curves
                if curve.name not in result.curves.names
            )
            plotted_names.extend(spec.variable_names)
        for variable_names in data:
            if variable_names not in plotted_names + list(MetaDataNames):
                if isinstance(data[variable_names], ndarray):
                    result.vectors[variable_names] = data[variable_names]
                else:
                    result.scalars[variable_names] = data[variable_names]

        for field_name in model.FIELDS_FROM_FILE:
            result.fields[field_name] = [
                (
                    MeshField.load(
                        Path(
                            archive_result["metadata"][
                                MetaDataNames.directory_archive_job
                            ]
                        )
                        / file_name
                    )
                    if load_fields
                    else file_name
                )
                for file_name in atleast_1d(data[field_name])
            ]

        return result

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Return the raw data of the result.

        Returns:
            The inputs, the outputs and the metadata, as in an archive, from which
            :meth:`from_dict` rebuilds the result.
        """
        archive_manager = DirectoryArchive(PersistencyPolicy.DELETE_ALWAYS, "", "")
        return archive_manager._prepare_archive_result(self.archived_data)

    def get_plot_choices(self) -> dict[str, list[str]]:
        return {"plot_names": self.plots.names}

    def _create_figures(self, settings: ModelResultPlotSettings) -> dict[str, Figure]:
        from vimseo.utilities.plotting_utils import superpose_curves

        return {
            curve_set.name: superpose_curves(curve_set, save=False, show=False)
            for curve_set in self.plots
            if not settings.plot_names or curve_set.name in settings.plot_names
        }

    def _create_tables(self) -> dict[str, DataFrame]:
        tables = {
            group: DataFrame([self.scalars(group=group)])
            for group in ("inputs", "outputs")
        }
        tables["metadata"] = DataFrame([
            {name: self._get_metadata(name) for name in self.metadata.report}
        ])
        return tables

    def __str__(self):
        text = MultiLineString()
        text.add("")
        text.add("Scalars:")
        text.add(str(dict(self.scalars)))
        text.add("")
        text.add("Vectors:")
        text.add(str(dict(self.vectors)))
        text.add("")
        text.add("Curves:")
        text.indent()
        for curve in self.curves:
            text.add(str(curve.variable_names))
            text.add(str(curve))
            text.add("")
        text.dedent()
        text.add("Fields:")
        text.add(str(self.fields))
        return str(text)
