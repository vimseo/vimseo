# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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
import pickle
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import fields
from io import BytesIO
from math import isnan
from pathlib import Path
from typing import TYPE_CHECKING

import h5py
import matplotlib
import numpy as np
import pandas as pd
import pytest
from docstring_inheritance import GoogleDocstringInheritanceMeta
from gemseo.datasets.dataset import Dataset

from vimseo.tools.metadata import ToolResultMetadata
from vimseo.tools.serializer import deserialize_value
from vimseo.tools.serializer import serialize_value
from vimseo.utilities.datasets import assert_frame_equal_unordered

if TYPE_CHECKING:
    from io import IOBase

LOGGER = logging.getLogger(__name__)


@dataclass
class BaseResult(metaclass=GoogleDocstringInheritanceMeta):
    """A result of a tool (:class:`.BaseTool`).

    This result is the object that flows through a workflow of tools.
    It is self-supporting and carries information on how to process it through the
    :attr:`.ToolResultMetadata.settings`. The result can be written on disk in binary format
    (``pickle``) and its metadata can also be written on disk in a readable format
    (``json``).
    """

    metadata: ToolResultMetadata | None = None
    """ToolResultMetadata attached to a result."""

    def to_pickle(self, file_path):
        """Save result instance to disk."""
        with Path(file_path).open("wb") as f:
            pickle.dump(self, f)

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
        """Serialization of a BaseResult to a hdf5 buffer."""
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

    def __post_init__(self):
        self.metadata = ToolResultMetadata()


def assert_results_equal(r1, r2):
    """Compare récursivement deux dataclasses/dicts/arrays."""
    if dataclasses.is_dataclass(r1):
        assert type(r1) is type(r2)
        for fld in dataclasses.fields(r1):
            if fld.name == "generic":
                continue
            print("Compared field:", fld.name)
            assert_results_equal(getattr(r1, fld.name), getattr(r2, fld.name))
    elif isinstance(r1, matplotlib.figure.Figure):
        # Figures are not comparable, only the type is checked
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
            assert r1 == pytest.approx(r2)
        else:
            assert isnan(r2)
    else:
        try:
            assert r1 == r2
        except (AssertionError, TypeError, ValueError) as e:
            # If comparison returns an error or a non-boolean, check the type and print
            # that the comparison has failed.
            assert type(r1) is type(r2), (  # noqa: PT017
                f"Objects of type {type(r1)} are not equal and not comparable: {e}"
            )
