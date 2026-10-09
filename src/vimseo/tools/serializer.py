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

import base64
import dataclasses
import importlib
import json
import logging
import pickle
from collections import OrderedDict
from datetime import date
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import numpy as np
import pandas as pd
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from pydantic import BaseModel

from vimseo.tools.space.random_variable_interface import add_deterministic_from_dict
from vimseo.tools.space.random_variable_interface import add_distributions_from_dict
from vimseo.tools.space.random_variable_interface import deterministic_to_dict
from vimseo.tools.space.random_variable_interface import distributions_to_dict
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder
from vimseo.utilities.ot_distribution_io import is_ot_distribution
from vimseo.utilities.ot_distribution_io import ot_distribution_from_dict
from vimseo.utilities.ot_distribution_io import ot_distribution_to_dict

if TYPE_CHECKING:
    import h5py

LOGGER = logging.getLogger(__name__)


def _class_path(cls: type) -> str:
    """Return the fully qualified ``module.qualname`` of a class."""
    return f"{cls.__module__}.{cls.__qualname__}"


def _import_class(class_path: str) -> type:
    """Import a class from its ``module.qualname`` path.

    The lookup tries, from the longest to the shortest module-name prefix, to
    import the module and then walk the remaining dotted attributes. This
    supports both top-level classes and classes nested inside another class.

    Args:
        class_path: The fully qualified class path, e.g.
            ``"vimseo.utilities.distribution.DistributionSettings"``.

    Returns:
        The imported class.

    Raises:
        ImportError: If no prefix of ``class_path`` resolves to an importable
            module exposing the remaining attributes.
    """
    parts = class_path.split(".")
    for i in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:i])
        attr_parts = parts[i:]
        try:
            obj = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        try:
            for part in attr_parts:
                obj = getattr(obj, part)
        except AttributeError:
            continue
        return obj
    msg = f"Cannot import class from '{class_path}'"
    raise ImportError(msg)


def __to_dataframe(value: pd.DataFrame, key: str, group: h5py.Group, type_name: str):
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

    if isinstance(value.index, pd.RangeIndex):
        # Stored by its parameters, so that it is read back as a RangeIndex and not
        # as an Index of integers, which is a different type.
        sub.attrs["index_range"] = json.dumps([
            value.index.start,
            value.index.stop,
            value.index.step,
        ])
    else:
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
            # Pandas masked dtypes (Int64, Float64, boolean, ...) cannot be
            # written as-is to HDF5: store them as float + NaN, which
            # losslessly round-trips through `pd.array(..., dtype=...)`, and
            # remember the original dtype to restore it on read.
            if hasattr(col_data.dtype, "numpy_dtype"):
                data = col_data.to_numpy(dtype=float, na_value=np.nan)
            else:
                data = col_data.values
            cols_group.create_dataset(col_key, data=data)
            if hasattr(col_data.dtype, "numpy_dtype"):
                cols_group[col_key].attrs["dtype"] = str(col_data.dtype)
            # Add human-readable column name as attribute
            cols_group[col_key].attrs["column_name"] = (
                json.dumps(list(col)) if is_multiindex else str(col)
            )


def __from_dataframe(item: h5py.Group) -> pd.DataFrame:
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
    if "index_range" in item.attrs:
        index = pd.RangeIndex(*json.loads(item.attrs["index_range"]))
    cols_group = item["columns_data"]
    data = {}
    for i, col in enumerate(columns):
        col_key = str(i)
        if f"__type__{col_key}" in cols_group.attrs:
            data[col] = json.loads(cols_group.attrs[col_key])
        else:
            raw = cols_group[col_key][()]
            dtype_attr = cols_group[col_key].attrs.get("dtype")
            data[col] = pd.array(raw, dtype=dtype_attr) if dtype_attr else raw

    df = pd.DataFrame(data, columns=columns)
    if index is not None:
        df.index = index

    return df


def _encode_dict_key(k: Any) -> tuple[str, Any] | None:
    """Return ``(type_name, json_value)`` for a non-``str`` dict key.

    Returns:
        ``None`` if the key type is not supported, in which case the key is
        stored as its ``str()`` form and cannot be restored exactly.
    """
    if isinstance(k, bool):
        return "bool", k
    if isinstance(k, (int, np.integer)):
        return "int", int(k)
    if isinstance(k, (float, np.floating)):
        return "float", float(k)
    if isinstance(k, tuple):
        try:
            return "tuple", json.dumps(list(k), cls=EnhancedJSONEncoder)
        except TypeError:
            return None
    return None


def _decode_dict_key(type_name: str, value: Any) -> Any:
    """Reconstruct a non-``str`` dict key from its encoded form."""
    if type_name == "bool":
        return bool(value)
    if type_name == "int":
        return int(value)
    if type_name == "float":
        return float(value)
    if type_name == "tuple":
        return tuple(json.loads(value))
    return value


def _pickle_fallback(group: h5py.Group, key: str, value: Any) -> None:
    """Serialize a value as a pickle blob, the last-resort fallback."""
    try:
        data = np.frombuffer(pickle.dumps(value), dtype=np.uint8)
        LOGGER.info(f"PICKLE fallback: key='{key}', type={type(value)}, value={value}")
        group.create_dataset(key, data=data)
        group[key].attrs["__type__"] = "pickle"
    except (pickle.PicklingError, TypeError) as e:
        # Non serializable, store None
        LOGGER.warning(f"Cannot pickle key='{key}', type={type(value)}: {e}")
        group.attrs[key] = "__null__"
        group.attrs[f"__type__{key}"] = "null"


def _serialize_space(group: h5py.Group, key: str, space: DesignSpace) -> None:
    """Serialize a ``DesignSpace``/``ParameterSpace`` in clear.

    Deterministic variables are described through their bounds/type/size/
    current value (:func:`deterministic_to_dict`); for a ``ParameterSpace``,
    uncertain variables are described through the ``vimseo_settings``
    attached to their marginals by :func:`add_random_variable_interface`
    (:func:`distributions_to_dict`).

    If the space contains a variable that was not built through vimseo's own
    API -- so it carries no ``vimseo_settings`` -- or an unsupported
    ``InterfacedDistribution`` vector, the *whole* space falls back to a
    single pickle blob rather than a partial, fragile reconstruction: gemseo
    does not expose a public API to graft one already-built random variable
    back into a space without replaying its own (private) bookkeeping.
    """
    is_parameter_space = isinstance(space, ParameterSpace)
    uncertain = None
    if is_parameter_space:
        try:
            uncertain = distributions_to_dict(space)
        except (AttributeError, ValueError) as e:
            LOGGER.info(
                f"PICKLE fallback: key='{key}', type={type(space).__name__}: "
                f"its distributions could not be described in clear ({e})."
            )
            _pickle_fallback(group, key, space)
            return

    sub = group.require_group(key)
    sub.attrs["__type__"] = "parameter_space" if is_parameter_space else "design_space"
    sub.attrs["__class__"] = _class_path(type(space))
    serialize_value(sub, "deterministic", deterministic_to_dict(space))
    if is_parameter_space:
        serialize_value(sub, "uncertain", uncertain)


def _serialize_ot_distribution(group: h5py.Group, key: str, distribution) -> None:
    """Serialize an OpenTURNS distribution in clear.

    The distribution is described by :func:`ot_distribution_to_dict`. If it cannot
    be described in clear, e.g. a ``DeconditionedDistribution``, it falls back to a
    pickle blob.
    """
    try:
        description = ot_distribution_to_dict(distribution)
    except ValueError as error:
        LOGGER.info(f"PICKLE fallback: key='{key}': {error}")
        _pickle_fallback(group, key, distribution)
        return

    sub = group.require_group(key)
    sub.attrs["__type__"] = "ot_distribution"
    serialize_value(sub, "description", description)


def serialize_value(group: h5py.Group, key: str, value: Any) -> None:
    """Recurcively serialize a value in an HDF5 group."""

    if value is None:
        group.attrs[key] = "__null__"
        group.attrs[f"__type__{key}"] = "null"

    elif isinstance(value, np.ndarray):
        group.create_dataset(key, data=value)
        group[key].attrs["__type__"] = "ndarray"

    elif isinstance(value, Dataset):
        __to_dataframe(value, key, group, "dataset")

    elif isinstance(value, pd.DataFrame):
        __to_dataframe(value, key, group, "dataframe")

    elif isinstance(value, Enum):
        # Checked before the primitive branch: a StrEnum/IntEnum member would
        # otherwise be caught there and come back as a plain str/int.
        raw = value.value
        group.attrs[key] = raw if isinstance(raw, (str, int, float, bool)) else str(raw)
        group.attrs[f"__type__{key}"] = "enum"
        group.attrs[f"__class__{key}"] = _class_path(type(value))

    elif isinstance(value, datetime):
        # Checked before ``date``, which ``datetime`` is a subclass of.
        group.attrs[key] = value.isoformat()
        group.attrs[f"__type__{key}"] = "datetime"

    elif isinstance(value, date):
        group.attrs[key] = value.isoformat()
        group.attrs[f"__type__{key}"] = "date"

    elif isinstance(value, Path):
        group.attrs[key] = value.as_posix()
        group.attrs[f"__type__{key}"] = "path"

    elif isinstance(value, complex):
        group.attrs[key] = json.dumps([value.real, value.imag])
        group.attrs[f"__type__{key}"] = "complex"

    elif isinstance(value, bytes):
        group.attrs[key] = base64.b64encode(value).decode("ascii")
        group.attrs[f"__type__{key}"] = "bytes"

    elif isinstance(value, (set, frozenset)):
        group.attrs[key] = json.dumps(list(value), cls=EnhancedJSONEncoder)
        group.attrs[f"__type__{key}"] = (
            "frozenset" if isinstance(value, frozenset) else "set"
        )

    elif isinstance(value, dict):
        if key in group:
            del group[key]
        sub = group.create_group(key)
        sub.attrs["__type__"] = "dict"
        sub.attrs["__empty__"] = len(value) == 0
        sub.attrs["__ordered__"] = isinstance(value, OrderedDict)
        key_order = []
        key_types = {}
        for k, v in value.items():
            str_key = str(k)
            key_order.append(str_key)
            if not isinstance(k, str):
                encoded = _encode_dict_key(k)
                if encoded is not None:
                    key_types[str_key] = encoded
            serialize_value(sub, str_key, v)
        sub.attrs["__key_order__"] = json.dumps(key_order)
        if key_types:
            sub.attrs["__key_types__"] = json.dumps(key_types)

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
        sub.attrs["__class__"] = _class_path(type(value))
        for fld in dataclasses.fields(value):
            serialize_value(sub, fld.name, getattr(value, fld.name))

    elif isinstance(value, BaseModel):
        sub = group.require_group(key)
        sub.attrs["__type__"] = "pydantic"
        sub.attrs["__class__"] = _class_path(type(value))
        for name in type(value).model_fields:
            serialize_value(sub, name, getattr(value, name))

    elif isinstance(value, DesignSpace):
        # ParameterSpace is a DesignSpace subclass; checked after BaseModel
        # (it is neither) and before the pickle fallback.
        _serialize_space(group, key, value)

    elif is_ot_distribution(value):
        _serialize_ot_distribution(group, key, value)

    else:
        _pickle_fallback(group, key, value)


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
        if type_ == "enum":
            if key not in node.attrs:
                return None
            cls = _import_class(node.attrs[f"__class__{key}"])
            return cls(node.attrs[key])
        if type_ == "datetime":
            return (
                datetime.fromisoformat(node.attrs[key]) if key in node.attrs else None
            )
        if type_ == "date":
            return date.fromisoformat(node.attrs[key]) if key in node.attrs else None
        if type_ == "path":
            return Path(node.attrs[key]) if key in node.attrs else None
        if type_ == "complex":
            if key not in node.attrs:
                return None
            real, imag = json.loads(node.attrs[key])
            return complex(real, imag)
        if type_ == "bytes":
            return base64.b64decode(node.attrs[key]) if key in node.attrs else None
        if type_ in ("set", "frozenset"):
            if key not in node.attrs:
                return None
            items = json.loads(node.attrs[key])
            return frozenset(items) if type_ == "frozenset" else set(items)

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
        df = __from_dataframe(item)
        return Dataset.from_dataframe(df)

    if type_ == "dataframe":
        return __from_dataframe(item)

    if type_ == "dict":
        # Empty dict
        if item.attrs["__empty__"]:
            return OrderedDict() if item.attrs.get("__ordered__") else {}

        if "__key_order__" in item.attrs:
            key_order = json.loads(item.attrs["__key_order__"])
        else:
            # Legacy file, written before key order was tracked: fall back to
            # a deterministic (but not necessarily original) ordering.
            all_keys = set(item.keys())
            for attr_key in item.attrs:
                if attr_key.startswith("__type__") and attr_key != "__type__":
                    real_key = attr_key[len("__type__") :]
                    if real_key:
                        all_keys.add(real_key)
            key_order = sorted(all_keys)

        key_types = (
            json.loads(item.attrs["__key_types__"])
            if "__key_types__" in item.attrs
            else {}
        )

        result = OrderedDict() if item.attrs.get("__ordered__") else {}
        for str_key in key_order:
            real_key = str_key
            if str_key in key_types:
                type_name, raw = key_types[str_key]
                real_key = _decode_dict_key(type_name, raw)
            result[real_key] = deserialize_value(item, str_key)
        return result

    if type_ == "list":
        n = item.attrs["__len__"]
        return [deserialize_value(item, str(i)) for i in range(n)]

    if type_ == "ot_distribution":
        return ot_distribution_from_dict(deserialize_value(item, "description"))

    if type_ in ("dataclass", "pydantic"):
        cls = _import_class(item.attrs["__class__"])

        if type_ == "dataclass":
            field_names = [fld.name for fld in dataclasses.fields(cls)]
        else:
            field_names = list(cls.model_fields)

        kwargs = {}
        for name in field_names:
            if name in item or f"__type__{name}" in item.attrs:
                kwargs[name] = deserialize_value(item, name)
            elif type_ == "dataclass":
                fld = next(f for f in dataclasses.fields(cls) if f.name == name)
                if fld.default is not dataclasses.MISSING:
                    kwargs[name] = fld.default
                elif fld.default_factory is not dataclasses.MISSING:
                    kwargs[name] = fld.default_factory()
                else:
                    kwargs[name] = None
            else:
                model_field = cls.model_fields[name]
                kwargs[name] = (
                    None
                    if model_field.is_required()
                    else model_field.get_default(call_default_factory=True)
                )

        if type_ == "dataclass":
            # Avoid __post_init__ for all dataclasses, otherwise the settings
            # field is set to default value.
            obj = cls.__new__(cls)
            for k, v in kwargs.items():
                object.__setattr__(obj, k, v)
            return obj

        # ``model_construct`` skips validation and defaults/validators, so a
        # result read back is not re-validated against the current grammar.
        return cls.model_construct(**kwargs)

    if type_ in ("parameter_space", "design_space"):
        cls = _import_class(item.attrs["__class__"])
        space = cls()
        add_deterministic_from_dict(
            space, deserialize_value(item, "deterministic") or {}
        )
        if type_ == "parameter_space":
            add_distributions_from_dict(
                space, deserialize_value(item, "uncertain") or {}
            )
        return space

    if type_ == "pickle":
        return pickle.loads(item[()].tobytes())

    LOGGER.warning(f"Unhandled type '{type_}' for key '{key}'")
    return None
