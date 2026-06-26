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

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from numbers import Number
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.utils.string_tools import MultiLineString
from numpy import atleast_1d
from numpy import ndarray

from vimseo.api import create_model
from vimseo.core.model_metadata import MetaDataNames
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.storage_management.directory_storage import DirectoryArchive
from vimseo.tools.base_result import BaseResult
from vimseo.utilities.curves import Curve
from vimseo.utilities.fields import Field

if TYPE_CHECKING:
    from vimseo.core.base_integrated_model import IntegratedModel
    from vimseo.storage_management.base_archive_storage import ModelDataType

ScalarDataType = Mapping[str, float | int | str]


@dataclass
class ModelResult(BaseResult):
    """The result of a model execution in a user-friendly format.

    Scalars, vectors, curves and fields are stored separately in ease to handle objects.
    """

    scalars: ScalarDataType = field(default_factory=dict)
    vectors: Mapping[str, ndarray] = field(default_factory=dict)
    curves: Iterable[Curve] = field(default_factory=list)
    fields: Mapping[str, Iterable[Field | Path | str]] = field(default_factory=dict)
    snapshots: Iterable[Path | str] = field(default_factory=list)

    # TODO Add timestamp attr in Field, and fill this value based on a variable name
    #  representing time

    @classmethod
    def from_data(
        cls,
        model_data: ModelDataType,
        model: IntegratedModel | None = None,
        load_fields: bool = False,
    ) -> ModelResult:
        """Create a ModelResult from raw model data."""

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
        result = ModelResult()
        result.metadata.model = model.description
        for name in MetaDataNames:
            result.metadata.report[name] = archive_result["metadata"][name]
        data = dict(archive_result["inputs"], **archive_result["outputs"])
        for variables in model.curves:
            curve = Curve({
                variables[0]: data[variables[0]],
                variables[1]: data[variables[1]],
            })
            result.curves.append(curve)
        for variable_names in data:
            if variable_names not in [
                name for curve_names in model.curves for name in curve_names
            ] + list(MetaDataNames):
                if isinstance(data[variable_names], ndarray):
                    result.vectors[variable_names] = data[variable_names]
                else:
                    result.scalars[variable_names] = data[variable_names]

        for field_name in model.FIELDS_FROM_FILE:
            result.fields[field_name] = [
                (
                    Field.load(
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

    def get_curve(self, variable_names: tuple[str]) -> Curve:
        curves = [
            curve for curve in self.curves if curve.variable_names == variable_names
        ]
        if len(curves) == 0:
            return []
        return curves[0]

    def get_numeric_scalars(
        self, variable_names: Iterable[str] = ()
    ) -> Mapping[str, Number]:
        variable_names = (
            list(self.scalars.keys()) if len(variable_names) == 0 else variable_names
        )
        return {
            name: value
            for name, value in self.scalars.items()
            if isinstance(value, Number) and name in variable_names
        }

    def __str__(self):
        text = MultiLineString()
        text.add("")
        text.add("Scalars:")
        text.add(str(self.scalars))
        text.add("")
        text.add("Vectors:")
        text.add(str(self.vectors))
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
