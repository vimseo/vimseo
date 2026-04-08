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
import importlib
import json
import logging
import pickle
from typing import TYPE_CHECKING
from typing import Any

import numpy as np
import pandas as pd
from gemseo.datasets.dataset import Dataset
from gemseo.uncertainty.distributions.base_distribution import DistributionSettings

from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    import h5py

LOGGER = logging.getLogger(__name__)


def to_dataframe(value, key, group, type_name):
    """Serialize a Dataframe, possibly multi-index."""
    if key in group:
        del group[key]
    sub = group.create_group(key)
    sub.attrs["__type__"] = type_name

    is_multiindex = isinstance(value.columns, pd.MultiIndex)
    sub.attrs["is_multiindex"] = is_multiindex
    if is_multiindex:
        sub.attrs["columns"] = json.dumps(
            [list(c) for c in value.columns.tolist()], cls=EnhancedJSONEncoder
        )
        sub.attrs["multiindex_names"] = json.dumps(
            list(value.columns.names), cls=EnhancedJSONEncoder
        )
    else:
        sub.attrs["columns"] = json.dumps(list(value.columns), cls=EnhancedJSONEncoder)

    sub.attrs["index"] = json.dumps(list(value.index))

    cols_group = sub.require_group("columns_data")
    for i, col in enumerate(value.columns):
        col_data = value[col]
        col_key = str(i)

        if col_data.dtype == object:
            cols_group.attrs[col_key] = json.dumps(
                list(col_data), cls=EnhancedJSONEncoder
            )
            cols_group.attrs[f"__type__{col_key}"] = "json_col"
        else:
            cols_group.create_dataset(col_key, data=col_data.values)
            # Add human-readable column name as attribute
            cols_group[col_key].attrs["column_name"] = (
                json.dumps(list(col)) if is_multiindex else str(col)
            )


def from_dataframe(item):
    """Deserialize a Dataframe."""
    is_multiindex = item.attrs.get("is_multiindex", False)
    columns_raw = json.loads(item.attrs["columns"])

    if is_multiindex:
        names = json.loads(item.attrs.get("multiindex_names", "null"))
        columns = pd.MultiIndex.from_tuples(
            [tuple(c) for c in columns_raw], names=names
        )
    else:
        columns = columns_raw

    index = json.loads(item.attrs.get("index", "null") or "null")
    cols_group = item["columns_data"]
    data = {}
    for i, col in enumerate(columns):
        col_key = str(i)
        if f"__type__{col_key}" in cols_group.attrs:
            data[col] = json.loads(cols_group.attrs[col_key])
        else:
            data[col] = cols_group[col_key][()]

    df = pd.DataFrame(data, columns=columns)
    if index is not None:
        df.index = index

    return df


def serialize_value(group: h5py.Group, key: str, value: Any) -> None:
    """Recurcively serialize a value in an HDF5 group."""

    if value is None:
        group.attrs[key] = "__null__"
        group.attrs[f"__type__{key}"] = "null"

    elif isinstance(value, np.ndarray):
        group.create_dataset(key, data=value)
        group[key].attrs["__type__"] = "ndarray"

    elif isinstance(value, Dataset):
        to_dataframe(value, key, group, "dataset")

    elif isinstance(value, pd.DataFrame):
        to_dataframe(value, key, group, "dataframe")

    elif isinstance(value, dict):
        if key in group:
            del group[key]
        sub = group.create_group(key)
        sub.attrs["__type__"] = "dict"
        sub.attrs["__empty__"] = len(value) == 0
        for k, v in value.items():
            try:
                serialize_value(sub, str(k), v)
            except Exception:  # noqa: BLE001
                # Fallback pickle for non serializable values
                data = np.frombuffer(pickle.dumps(v), dtype=np.uint8)
                sub.create_dataset(str(k), data=data)
                sub[str(k)].attrs["__type__"] = "pickle"

    elif isinstance(value, tuple):
        group.attrs[key] = json.dumps(list(value), cls=EnhancedJSONEncoder)
        group.attrs[f"__type__{key}"] = "tuple"

    elif isinstance(value, list):
        sub = group.require_group(key)
        sub.attrs["__type__"] = "list"
        sub.attrs["__len__"] = len(value)
        for i, v in enumerate(value):
            serialize_value(sub, str(i), v)

    elif isinstance(
        value, (str, int, float, bool, np.integer, np.floating, np.bool_, np.str_)
    ):
        # Convert Numpy types in native Python types
        if isinstance(value, np.integer):
            value = int(value)
        elif isinstance(value, np.floating):
            value = float(value)
        elif isinstance(value, (np.bool_, bool)):
            value = bool(value)
        elif isinstance(value, (np.str_, str)):
            value = str(value)
        group.attrs[key] = value
        group.attrs[f"__type__{key}"] = "primitive"

    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        sub = group.require_group(key)
        sub.attrs["__type__"] = "dataclass"
        sub.attrs["__module__"] = f"{type(value).__module__}"
        sub.attrs["__class__"] = f"{type(value).__name__}"
        for fld in dataclasses.fields(value):
            serialize_value(sub, fld.name, getattr(value, fld.name))

    else:
        try:
            # Fallback pickle
            data = np.frombuffer(pickle.dumps(value), dtype=np.uint8)
            LOGGER.info(
                f"PICKLE fallback: key='{key}', type={type(value)}, value={value}"
            )
            group.create_dataset(key, data=data)
            group[key].attrs["__type__"] = "pickle"
        except (pickle.PicklingError, TypeError) as e:
            # Non serializable, store None
            LOGGER.warning(f"Cannot pickle key='{key}', type={type(value)}: {e}")
            group.attrs[key] = "__null__"
            group.attrs[f"__type__{key}"] = "null"


def deserialize_value(node: h5py.Group | h5py.Dataset, key: str) -> Any:
    """Recurcively deserialize a value from an HDF5 group."""

    if f"__type__{key}" in node.attrs:
        type_ = node.attrs[f"__type__{key}"]
        if type_ == "null":
            return None
        if type_ == "primitive":
            if key in node.attrs:
                return node.attrs[key]
            return None
        if type_ == "json":
            if key in node.attrs:
                return json.loads(node.attrs[key])
            return None
        if type_ == "tuple":
            if key in node.attrs:
                return tuple(json.loads(node.attrs[key]))
            return None

    if key not in node:
        return None

    item = node[key]
    type_ = item.attrs.get("__type__")

    if type_ == "ndarray":
        data = item[()]
        # Bytes to str conversion if necessary
        if data.dtype == object:
            vectorized = np.vectorize(
                lambda x: x.decode("utf-8") if isinstance(x, bytes) else x
            )
            data = vectorized(data)
        return data

    if type_ == "dataset":
        df = from_dataframe(item)
        return Dataset.from_dataframe(df)

    if type_ == "dataframe":
        return from_dataframe(item)

    # TODO handle distributions and parameter_space in a second time
    if type_ == "distribution":
        settings = DistributionSettings(**item)
        return type(settings.distribution_name)(settings=settings)

    if type_ == "dict":
        # Empty dict
        if item.attrs.get("__empty__", False):
            return {}

        all_keys = set(item.keys())
        for attr_key in item.attrs:
            if attr_key.startswith("__type__"):
                real_key = attr_key[len("__type__") :]
                if real_key:
                    all_keys.add(real_key)
        return {k: deserialize_value(item, k) for k in all_keys}

    if type_ == "list":
        n = item.attrs["__len__"]
        return [deserialize_value(item, str(i)) for i in range(n)]

    if type_ == "dataclass":
        if "__module__" in item.attrs:
            module_name = item.attrs["__module__"]
            class_path = item.attrs["__class__"]
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_path)
            except (ModuleNotFoundError, AttributeError) as e:
                msg = f"Cannot import dataclass '{class_path}' from module '{module_name}': {e}"
                raise ImportError(msg) from e

        else:
            # Fallback for older versions without __module__ attribute,
            # try to find the class by splitting the class path
            class_path = item.attrs["__class__"]
            module_name, _qualname = (
                class_path.rsplit(".", 1) if "." in class_path else (class_path, "")
            )

            # First simple search with rsplit,
            # Then traverse hierarchy for nested classes
            parts = class_path.split(".")

            # Find appropriate splitting module/class by trying from longest to shortest
            cls = None
            for i in range(len(parts) - 1, 0, -1):
                module_name = ".".join(parts[:i])
                class_parts = parts[i:]
                try:
                    module = importlib.import_module(module_name)
                    obj = module
                    for part in class_parts:
                        obj = getattr(obj, part)
                    cls = obj
                    break
                except (ModuleNotFoundError, AttributeError):
                    continue

        if cls is None:
            msg = f"Cannot import class from '{class_path}'"
            raise ImportError(msg)

        kwargs = {}
        for fld in dataclasses.fields(cls):
            if fld.name in item or f"__type__{fld.name}" in item.attrs:
                kwargs[fld.name] = deserialize_value(item, fld.name)
            else:
                if fld.default is not dataclasses.MISSING:
                    kwargs[fld.name] = fld.default
                elif fld.default_factory is not dataclasses.MISSING:
                    kwargs[fld.name] = fld.default_factory()
                else:
                    kwargs[fld.name] = None

        # Avoid __post_init__ for all dataclasses, otherwise the settings field is set
        # to default value.
        obj = cls.__new__(cls)
        for k, v in kwargs.items():
            object.__setattr__(obj, k, v)

        return obj

    if type_ == "pickle":
        return pickle.loads(item[()].tobytes())

    LOGGER.warning(f"Unhandled type '{type_}' for key '{key}'")
    return None
