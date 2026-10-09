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

import dataclasses
import json
import logging
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from io import BytesIO
from math import isclose
from math import isnan
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

import h5py
import matplotlib.figure
import numpy as np
import pandas as pd
from docstring_inheritance import GoogleDocstringInheritanceMeta
from gemseo.datasets.dataset import Dataset

from vimseo.tools.metadata import ToolResultMetadata
from vimseo.tools.result_visualization import BaseVisualizationSettings
from vimseo.tools.result_visualization import fields_to_dataframes
from vimseo.tools.result_visualization import flatten_figures
from vimseo.tools.result_visualization import save_figures
from vimseo.tools.result_visualization import settings_to_dataframe
from vimseo.tools.result_visualization import show_figures
from vimseo.tools.serializer import deserialize_value
from vimseo.tools.serializer import serialize_value
from vimseo.utilities.datasets import assert_frame_equal_unordered

if TYPE_CHECKING:
    from collections.abc import Mapping
    from io import IOBase

    from pandas import DataFrame

    from vimseo.tools.result_visualization import Figure

LOGGER = logging.getLogger(__name__)


@dataclass
class BaseResult(metaclass=GoogleDocstringInheritanceMeta):
    """A result of a tool (:class:`.BaseTool`).

    This result is the object that flows through a workflow of tools.
    It is self-supporting and carries information on how to process it through the
    :attr:`.ToolResultMetadata.settings`. The result can be written on disk in ``HDF5``
    format and its metadata can also be written on disk in a readable format
    (``json``).

    A result is visualized without the tool which produced it, for instance after
    being loaded from an archive: :meth:`visualize` returns its figures and
    :meth:`tabulate` its numerical values.
    """

    _VISUALIZATION_SETTINGS: ClassVar[type[BaseVisualizationSettings]] = (
        BaseVisualizationSettings
    )
    """The settings of :meth:`visualize`."""

    metadata: ToolResultMetadata = field(default_factory=ToolResultMetadata)
    """ToolResultMetadata attached to a result."""

    def visualize(
        self,
        settings: BaseVisualizationSettings | None = None,
        directory_path: str | Path = "",
        save: bool = False,
        show: bool = False,
        file_format: str = "html",
        **options: Any,
    ) -> dict[str, Figure]:
        """Create the figures of the result.

        Args:
            settings: The settings of the visualization.
                If ``None``, use the default settings, which show everything.
            directory_path: The path to the directory where the figures are saved.
                If empty, use the current working directory.
            save: Whether to save the figures, in files named after their keys.
            show: Whether to show the figures.
            file_format: The format of the plotly figures, ``"html"`` or an image
                format. The matplotlib figures are saved in ``"png"`` when the format
                is ``"html"``.
            **options: The settings of the visualization, overriding ``settings``.

        Returns:
            The figures.
        """
        figures = flatten_figures(
            self._create_figures(self.get_visualization_settings(settings, **options))
        )
        if not figures:
            LOGGER.debug(f"There is no figure to visualize {type(self).__name__}.")
        if save:
            save_figures(figures, directory_path or Path.cwd(), file_format)
        if show:
            show_figures(figures)
        return figures

    @classmethod
    def get_visualization_settings(
        cls, settings: BaseVisualizationSettings | None = None, **options: Any
    ) -> BaseVisualizationSettings:
        """Return the settings of the visualization.

        Args:
            settings: The settings of the visualization.
                If ``None``, use the default settings.
            **options: The settings of the visualization, overriding ``settings``.

        Returns:
            The validated settings.
        """
        settings_class = cls._VISUALIZATION_SETTINGS
        if settings is None:
            return settings_class(**options)
        return settings_class(**{**settings.model_dump(), **options})

    def get_key_values(self) -> dict[str, float]:
        """Return the few numbers summarizing the result.

        They are for instance the integrated metrics of a validation, or the
        criteria of a Bayesian analysis. They are logged as metrics by an MLflow
        archive of the tool results, so that the tool runs can be sorted, filtered
        and compared on them, and written in the summary of a directory archive.

        Returns:
            The finite numbers, bound to names whose levels are separated by dots,
            e.g. ``"RelativeErrorMetric.reaction_forces"``.
        """
        return {}

    def get_visualization_choices(self) -> dict[str, list[str]]:
        """Return the values available for the settings of the visualization.

        It is meant for the settings selecting names, e.g. variable names, so that a
        user interface can propose them.

        Returns:
            The names available for some settings, bound to the names of the settings.
        """
        return {}

    def _create_figures(
        self, settings: BaseVisualizationSettings
    ) -> Mapping[str, Figure | Mapping]:
        """Create the figures of the result, without saving nor showing them.

        Args:
            settings: The settings of the visualization.

        Returns:
            The figures, possibly nested in mappings.
        """
        return {}

    def tabulate(self) -> dict[str, DataFrame]:
        """Return the numerical values of the result as tables.

        Returns:
            The tables, including a table ``"settings"`` with the settings of the tool
            when there are some.
        """
        tables = self._create_tables()
        settings = settings_to_dataframe(self.metadata.settings)
        if settings is not None:
            tables["settings"] = settings
        return tables

    def _create_tables(self) -> dict[str, DataFrame]:
        """Create the tables of the numerical values of the result.

        By default, the fields which are tables, datasets or mappings with a tabular
        structure give a table named after the field,
        and the scalar fields are gathered in a table named ``"scalars"``.

        Returns:
            The tables.
        """
        return fields_to_dataframes(self)

    # TODO add an entry point to open myhdf5?
    def to_hdf5(self, path: str | Path) -> None:
        """Serialize a BaseResult into an HDF5 file.

        The file can be explored with an on-line reader,
        like <https://myhdf5.hdfgroup.org/>.
        For more information about hdf5, see
        [HDF5 documentation](https://docs.hdfgroup.org/hdf5/develop/)."""
        with h5py.File(path, "w") as f:
            f.attrs["__class__"] = type(self).__name__
            for fld in fields(self):
                serialize_value(f, fld.name, getattr(self, fld.name))

    def to_hdf5_buffer(self) -> BytesIO:
        """Serialize a BaseResult into an HDF5 buffer."""
        bio = BytesIO()
        with h5py.File(bio, "w") as f:
            f.attrs["__class__"] = type(self).__name__
            for fld in fields(self):
                serialize_value(f, fld.name, getattr(self, fld.name))

        return bio

    @classmethod
    def from_hdf5(cls, path: str | Path):
        """Deserialize from a file path."""
        with h5py.File(path, "r") as f:
            return cls._from_hdf5_file(f)

    @classmethod
    def from_hdf5_buffer(cls, buffer: IOBase | bytes):
        """Deserialize from a file-like object or bytes (e.g. Streamlit uploader)."""
        if isinstance(buffer, bytes):
            buffer = BytesIO(buffer)
        else:
            buffer.seek(0)
        with h5py.File(BytesIO(buffer.read()), "r") as f:
            return cls._from_hdf5_file(f)

    @classmethod
    def _from_hdf5_file(cls, f: h5py.File):
        """Common deserialization logic. Avoid passing in __post_init__()."""
        kwargs = {fld.name: deserialize_value(f, fld.name) for fld in fields(cls)}
        obj = cls.__new__(cls)
        for k, v in kwargs.items():
            object.__setattr__(obj, k, v)
        return obj

    # TODO move to BaseTool such that it can be exported to the working directory
    def save_metadata_to_disk(self, file_path: Path | str = ""):
        """Save metadata to disk in a readable format."""
        file_path = Path.cwd() if file_path == "" else Path(file_path)
        with Path(file_path / f"{self.__class__.__name__}_metadata.json").open(
            "w"
        ) as f:
            json.dump(asdict(self.metadata), f, indent=4, ensure_ascii=True)


def assert_results_equal(r1, r2):
    """Recursively compare two dataclasses/dicts/arrays."""
    if dataclasses.is_dataclass(r1):
        assert type(r1) is type(r2)
        for fld in dataclasses.fields(r1):
            if fld.name == "generic":
                continue
            LOGGER.info(f"Compared field: {fld.name}")
            assert_results_equal(getattr(r1, fld.name), getattr(r2, fld.name))
    elif isinstance(r1, matplotlib.figure.Figure):
        LOGGER.info("Figures are not comparable, only the type is checked")
        assert type(r1) is type(r2)
    elif isinstance(r1, np.ndarray):
        np.testing.assert_array_equal(r1, r2)
    elif isinstance(r1, Dataset):
        # Serialization of GEMSEO Dataset does not preserve column order
        assert_frame_equal_unordered(r1, r2)
    elif isinstance(r1, pd.DataFrame):
        pd.testing.assert_frame_equal(r1, r2)
    elif isinstance(r1, dict):
        assert set(r1.keys()) == set(r2.keys())
        for k in r1:
            assert_results_equal(r1[k], r2[k])
    elif isinstance(r1, list):
        assert len(r1) == len(r2)
        for v1, v2 in zip(r1, r2, strict=False):
            assert_results_equal(v1, v2)
    elif isinstance(r1, float):
        if not isnan(r1):
            assert isclose(r1, r2, rel_tol=1e-6, abs_tol=1e-12), f"{r1} != {r2}"
        else:
            assert isnan(r2)
    else:
        try:
            assert r1 == r2
        except (AssertionError, TypeError, ValueError) as e:
            # If comparison returns an error or a non-boolean, check the type and print
            # that the comparison has failed.
            assert type(r1) is type(r2), (  # ruff: ignore[pytest-assert-in-except]
                f"Objects of type {type(r1)} are not equal and not comparable: {e}"
            )
