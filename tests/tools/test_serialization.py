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

"""Tests for BaseResult HDF5 serialization/deserialization."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path

import h5py
import numpy as np
import openturns as ot
import pandas as pd
import pytest
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from pydantic import BaseModel

from vimseo.core.load_case import LoadCase
from vimseo.core.model_description import ModelDescription
from vimseo.material.material import Material
from vimseo.material.material_property import MaterialProperty
from vimseo.material.material_relation import MaterialRelation
from vimseo.tools.base_result import BaseResult
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.bayes.bayes_analysis_result import BayesAnalysisResult
from vimseo.tools.io.material_result import MaterialResult
from vimseo.tools.metadata import ToolResultMetadata
from vimseo.tools.sensitivity.sensitivity_result import SensitivityResult
from vimseo.tools.serializer import deserialize_value
from vimseo.tools.serializer import serialize_value
from vimseo.tools.space.random_variable_interface import add_random_variable_interface
from vimseo.tools.space.space_tool_result import SpaceToolResult
from vimseo.tools.statistics.statistics_result import StatisticsResult
from vimseo.tools.validation.validation_point_result import ValidationPointResult
from vimseo.tools.validation_case.validation_case_result import ValidationCaseResult
from vimseo.utilities.datasets import assert_frame_equal_unordered
from vimseo.utilities.distribution import DistributionParameters
from vimseo.utilities.distribution import DistributionSettings
from vimseo.utilities.distribution import InterfacedDistributionSettings


@pytest.fixture
def tmp_hdf5(tmp_path):
    """Return a temporary HDF5 file path."""
    return str(tmp_path / "result.h5")


def roundtrip(result: BaseResult, tmp_hdf5: str) -> BaseResult:
    """Write then read back a result."""
    result.to_hdf5(tmp_hdf5)
    return type(result).from_hdf5(tmp_hdf5)


# ---------------------------------------------------------------------------
# Tests — primitives and None
# ---------------------------------------------------------------------------


class TestPrimitivesAndNone:
    def test_none_field_roundtrip(self, tmp_hdf5):
        result = BayesAnalysisResult(thin_number=None)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.thin_number is None

    def test_int_field_roundtrip(self, tmp_hdf5):
        result = BayesAnalysisResult(thin_number=5, ndim=3)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.thin_number == 5
        assert rt.ndim == 3

    def test_float_field_roundtrip(self, tmp_hdf5):
        result = BayesAnalysisResult(lppd=1.23, ml=-4.56)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.lppd == pytest.approx(1.23)
        assert rt.ml == pytest.approx(-4.56)

    def test_str_field_roundtrip(self, tmp_hdf5):
        result = StatisticsResult(best_fitting_distributions=None)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.best_fitting_distributions is None


# ---------------------------------------------------------------------------
# Tests — numpy arrays
# ---------------------------------------------------------------------------


class TestNumpyArrays:
    def test_1d_array(self, tmp_hdf5):
        arr = np.array([1.0, 2.0, 3.0])
        result = BayesAnalysisResult(raw_samples=arr)
        rt = roundtrip(result, tmp_hdf5)
        np.testing.assert_array_equal(rt.raw_samples, arr)

    def test_2d_array(self, tmp_hdf5):
        arr = np.linspace(0, 4, 40).reshape((10, 4))
        result = BayesAnalysisResult(raw_samples=arr)
        rt = roundtrip(result, tmp_hdf5)
        np.testing.assert_array_almost_equal(rt.raw_samples, arr)

    def test_empty_array(self, tmp_hdf5):
        arr = np.empty((0, 3))
        result = BayesAnalysisResult(raw_samples=arr)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.raw_samples.shape == (0, 3)

    def test_integer_array(self, tmp_hdf5):
        arr = np.array([1, 2, 3], dtype=int)
        result = BayesAnalysisResult(processed_samples=arr)
        rt = roundtrip(result, tmp_hdf5)
        np.testing.assert_array_equal(rt.processed_samples, arr)


# ---------------------------------------------------------------------------
# Tests — DataFrames
# ---------------------------------------------------------------------------


class TestDataFrames:
    dataset = Dataset.from_array(
        data=np.array([[0.0, 1.0, 2.0, 2.1, 3.0, 3.1], [4.0, 5.0, 6.0, 6.1, 7.0, 7.1]]),
        variable_names=["a", "b", "c", "d"],
        variable_names_to_group_names={
            "a": IODataset.INPUT_GROUP,
            "b": IODataset.OUTPUT_GROUP,
            "c": IODataset.OUTPUT_GROUP,
            "d": IODataset.OUTPUT_GROUP,
        },
        variable_names_to_n_components={"a": 1, "b": 1, "c": 2, "d": 2},
    )

    dataset_w_duplicated_names = Dataset.from_array(
        data=np.array([[0.0, 2.0, 2.1, 3.0, 3.1], [4.0, 6.0, 6.1, 7.0, 7.1]]),
        variable_names=["a", "b", "c"],
        variable_names_to_group_names={
            "a": IODataset.OUTPUT_GROUP,
            "b": IODataset.OUTPUT_GROUP,
            "c": IODataset.OUTPUT_GROUP,
        },
        variable_names_to_n_components={"a": 1, "b": 2, "c": 2},
    )
    dataset_w_duplicated_names.add_variable(
        variable_name="a", group_name=IODataset.INPUT_GROUP, data=[1.0, 5.0]
    )

    def test_simple_dataframe(self, tmp_hdf5):
        df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        result = ValidationPointResult(measured_data=df)
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df)

    def test_range_index_is_kept(self, tmp_hdf5):
        """Check that the index is read back with the type it had, in both ways of
        the comparison: a RangeIndex is not equivalent to an Index of integers."""
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        assert isinstance(df.index, pd.RangeIndex)
        result = ValidationPointResult(measured_data=df)
        rt = roundtrip(result, tmp_hdf5)
        assert isinstance(rt.measured_data.index, pd.RangeIndex)
        pd.testing.assert_frame_equal(rt.measured_data, df)
        pd.testing.assert_frame_equal(df, rt.measured_data)

    def test_other_indexes_are_kept(self, tmp_hdf5):
        df = pd.DataFrame({"a": [1.0, 2.0]}, index=[10, 20])
        rt = roundtrip(ValidationPointResult(measured_data=df), tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df)
        pd.testing.assert_frame_equal(df, rt.measured_data)

        df = pd.DataFrame({"a": [1.0, 2.0]}, index=["u", "v"])
        rt = roundtrip(ValidationPointResult(measured_data=df), tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df)

    def test_dataframe_column_names_preserved(self, tmp_hdf5):
        df = pd.DataFrame({"x": [1.0], "y": [2.0], "z": [3.0]})
        result = ValidationPointResult(simulated_data=df)
        rt = roundtrip(result, tmp_hdf5)
        assert list(rt.simulated_data.columns) == ["x", "y", "z"]

    def test_multiple_dataframe_fields(self, tmp_hdf5):
        df1 = pd.DataFrame({"a": [1.0, 2.0]})
        df2 = pd.DataFrame({"b": [3.0, 4.0]})
        result = ValidationPointResult(measured_data=df1, simulated_data=df2)
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df1)
        pd.testing.assert_frame_equal(rt.simulated_data, df2)

    def test_dataframe_with_none(self, tmp_hdf5):
        result = ValidationPointResult(measured_data=None)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.measured_data is None

    def test_statistics_dataframe(self, tmp_hdf5):
        df = pd.DataFrame({"mean": [1.0, 2.0], "std": [0.1, 0.2]})
        result = StatisticsResult(statistics=df)
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.statistics, df)

    def test_simple_dataset(self, tmp_hdf5):
        result = ValidationPointResult(measured_data=self.dataset)
        rt = roundtrip(result, tmp_hdf5)
        assert_frame_equal_unordered(rt.measured_data, self.dataset)

    def test_dataset_w_duplicated_names(self, tmp_hdf5):
        result = ValidationPointResult(measured_data=self.dataset_w_duplicated_names)
        rt = roundtrip(result, tmp_hdf5)
        assert_frame_equal_unordered(rt.measured_data, self.dataset_w_duplicated_names)


# ---------------------------------------------------------------------------
# Tests — pandas nullable (masked) dtypes
# ---------------------------------------------------------------------------


class TestNullableDtypes:
    """Pandas masked dtypes (e.g. gemseo's Database.to_dataset() casts integer
    outputs to "Int64" so that NaN can coexist with valid integers) must survive
    an HDF5 round-trip with their original dtype, not silently degrade to a
    plain numpy dtype.
    """

    def test_int64_no_na(self, tmp_hdf5):
        df = pd.DataFrame({"a": pd.array([1, 2, 3], dtype="Int64")})
        result = ValidationPointResult(measured_data=df)
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df)

    def test_int64_with_na(self, tmp_hdf5):
        df = pd.DataFrame({"a": pd.array([1, None, 3], dtype="Int64")})
        result = ValidationPointResult(measured_data=df)
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df)

    def test_float64_with_na(self, tmp_hdf5):
        df = pd.DataFrame({"a": pd.array([1.5, None, 3.5], dtype="Float64")})
        result = ValidationPointResult(measured_data=df)
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df)

    def test_boolean_with_na(self, tmp_hdf5):
        df = pd.DataFrame({"a": pd.array([True, False, None], dtype="boolean")})
        result = ValidationPointResult(measured_data=df)
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.measured_data, df)


# ---------------------------------------------------------------------------
# Tests — dicts and nested structures
# ---------------------------------------------------------------------------


class TestDictsAndNestedStructures:
    def test_dict_of_primitives(self, tmp_hdf5):
        result = StatisticsResult(
            best_fitting_distributions={"x": "normal", "y": "uniform"}
        )
        rt = roundtrip(result, tmp_hdf5)
        assert rt.best_fitting_distributions == {"x": "normal", "y": "uniform"}

    def test_mapping_str_int(self, tmp_hdf5):
        dims = {"x": 1, "y": 3, "z": 2}
        result = SensitivityResult(variable_dimensions=dims)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.variable_dimensions == dims

    def test_nested_mapping_float(self, tmp_hdf5):
        metrics = {"var1": {"rmse": 0.1, "mae": 0.05}, "var2": {"rmse": 0.2}}
        result = ValidationPointResult(integrated_metrics=metrics)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.integrated_metrics == metrics

    def test_empty_dict(self, tmp_hdf5):
        result = SensitivityResult(variable_dimensions={})
        rt = roundtrip(result, tmp_hdf5)
        assert rt.variable_dimensions == {}

    def test_ordered_dict(self, tmp_hdf5):
        od = OrderedDict([("b", 2.0), ("a", 1.0)])
        result = StatisticsResult(statistics=od)
        rt = roundtrip(result, tmp_hdf5)
        assert dict(rt.statistics) == dict(od)

    def test_curve_data_type(self, tmp_hdf5):
        """Mapping[str, list[Mapping[str, DataFrame]]] — complex nested structure."""
        df1 = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
        df2 = pd.DataFrame({"x": [5.0, 6.0], "y": [7.0, 8.0]})
        curve_data = {
            "curve_A": [{"segment_1": df1}, {"segment_2": df2}],
            "curve_B": [{"segment_1": df1}],
        }

        @dataclass
        class ResultWithCurve(BaseResult):
            curve_data: dict | None = None

        result = ResultWithCurve(curve_data=curve_data)
        rt = roundtrip(result, tmp_hdf5)

        pd.testing.assert_frame_equal(rt.curve_data["curve_A"][0]["segment_1"], df1)
        pd.testing.assert_frame_equal(rt.curve_data["curve_A"][1]["segment_2"], df2)
        pd.testing.assert_frame_equal(rt.curve_data["curve_B"][0]["segment_1"], df1)

    def test_nominal_data_mixed_types(self, tmp_hdf5):
        """Mapping[str, float | int | ndarray]."""
        arr = np.array([1.0, 2.0, 3.0])
        nominal = {"temperature": 300.0, "pressure": 101325, "field": arr}
        result = ValidationPointResult(nominal_data=nominal)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.nominal_data["temperature"] == pytest.approx(300.0)
        assert rt.nominal_data["pressure"] == 101325
        np.testing.assert_array_equal(rt.nominal_data["field"], arr)


# ---------------------------------------------------------------------------
# Tests — types that used to fall back to pickle, now serialized in clear
# ---------------------------------------------------------------------------


class _Color(str, Enum):
    """A str-subclassing enum, like the ``StrEnum`` classes used in vimseo."""

    RED = "red"
    BLUE = "blue"


class _Status(Enum):
    """A plain (non-str) enum."""

    OK = 1
    FAILED = 2


class _InnerModel(BaseModel):
    """A pydantic model nested inside another one, for codec tests below."""

    value: float = 0.0


class _OuterModel(BaseModel):
    """A pydantic model whose field holds another pydantic model."""

    name: str = ""
    inner: _InnerModel = _InnerModel()


class TestClearCodecs:
    def test_str_enum_roundtrip(self, tmp_hdf5):
        @dataclass
        class ResultWithEnum(BaseResult):
            color: _Color | None = None

        result = ResultWithEnum(color=_Color.BLUE)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.color is _Color.BLUE
        assert isinstance(rt.color, _Color)

    def test_plain_enum_roundtrip(self, tmp_hdf5):
        @dataclass
        class ResultWithEnum(BaseResult):
            status: _Status | None = None

        result = ResultWithEnum(status=_Status.FAILED)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.status is _Status.FAILED

    def test_path_roundtrip(self, tmp_hdf5):
        @dataclass
        class ResultWithPath(BaseResult):
            path: Path | None = None

        result = ResultWithPath(path=Path("some") / "nested" / "file.txt")
        rt = roundtrip(result, tmp_hdf5)
        assert rt.path == Path("some") / "nested" / "file.txt"
        assert isinstance(rt.path, Path)

    def test_datetime_roundtrip(self, tmp_hdf5):
        from datetime import datetime

        @dataclass
        class ResultWithDatetime(BaseResult):
            timestamp: datetime | None = None

        ts = datetime(2026, 1, 2, 3, 4, 5)
        result = ResultWithDatetime(timestamp=ts)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.timestamp == ts

    def test_date_roundtrip(self, tmp_hdf5):
        from datetime import date

        @dataclass
        class ResultWithDate(BaseResult):
            day: date | None = None

        result = ResultWithDate(day=date(2026, 1, 2))
        rt = roundtrip(result, tmp_hdf5)
        assert rt.day == date(2026, 1, 2)

    def test_complex_roundtrip(self, tmp_hdf5):
        @dataclass
        class ResultWithComplex(BaseResult):
            value: complex | None = None

        result = ResultWithComplex(value=1.5 - 2.5j)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.value == pytest.approx(1.5 - 2.5j)

    def test_bytes_roundtrip(self, tmp_hdf5):
        @dataclass
        class ResultWithBytes(BaseResult):
            data: bytes | None = None

        result = ResultWithBytes(data=b"\x00\x01\xffvimseo")
        rt = roundtrip(result, tmp_hdf5)
        assert rt.data == b"\x00\x01\xffvimseo"

    def test_set_roundtrip(self, tmp_hdf5):
        @dataclass
        class ResultWithSet(BaseResult):
            names: set | None = None

        result = ResultWithSet(names={"a", "b", "c"})
        rt = roundtrip(result, tmp_hdf5)
        assert rt.names == {"a", "b", "c"}
        assert isinstance(rt.names, set)

    def test_frozenset_roundtrip(self, tmp_hdf5):
        @dataclass
        class ResultWithFrozenset(BaseResult):
            names: frozenset | None = None

        result = ResultWithFrozenset(names=frozenset({"a", "b"}))
        rt = roundtrip(result, tmp_hdf5)
        assert rt.names == frozenset({"a", "b"})
        assert isinstance(rt.names, frozenset)

    def test_ordered_dict_preserves_type_and_order(self, tmp_hdf5):
        od = OrderedDict([("z", 1.0), ("a", 2.0), ("m", 3.0)])

        @dataclass
        class ResultWithOrderedDict(BaseResult):
            data: dict | None = None

        result = ResultWithOrderedDict(data=od)
        rt = roundtrip(result, tmp_hdf5)
        assert isinstance(rt.data, OrderedDict)
        assert list(rt.data.items()) == list(od.items())

    def test_plain_dict_preserves_insertion_order(self, tmp_hdf5):
        d = {"z": 1.0, "a": 2.0, "m": 3.0}

        @dataclass
        class ResultWithDict(BaseResult):
            data: dict | None = None

        result = ResultWithDict(data=d)
        rt = roundtrip(result, tmp_hdf5)
        assert type(rt.data) is dict
        assert list(rt.data.items()) == list(d.items())

    def test_dict_with_int_keys_roundtrip(self, tmp_hdf5):
        d = {1: "one", 2: "two"}

        @dataclass
        class ResultWithIntKeys(BaseResult):
            data: dict | None = None

        result = ResultWithIntKeys(data=d)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.data == d
        assert all(isinstance(k, int) for k in rt.data)

    def test_dict_with_tuple_keys_roundtrip(self, tmp_hdf5):
        d = {(1, 2): "a", (3, 4): "b"}

        @dataclass
        class ResultWithTupleKeys(BaseResult):
            data: dict | None = None

        result = ResultWithTupleKeys(data=d)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.data == d
        assert all(isinstance(k, tuple) for k in rt.data)

    def test_pydantic_model_roundtrip_is_not_pickled(self, tmp_hdf5):
        """The concrete motivating case: DistributionSettings must be clear."""
        from vimseo.utilities.distribution import DistributionSettings

        settings = DistributionSettings(name="Normal", mu=1.0, sigma=0.05)

        @dataclass
        class ResultWithDistribution(BaseResult):
            settings: DistributionSettings | None = None

        result = ResultWithDistribution(settings=settings)
        result.to_hdf5(tmp_hdf5)
        with h5py.File(tmp_hdf5, "r") as f:
            assert f["settings"].attrs["__type__"] == "pydantic"
        rt = type(result).from_hdf5(tmp_hdf5)
        assert rt.settings == settings
        assert isinstance(rt.settings, DistributionSettings)

    def test_interfaced_distribution_settings_roundtrip(self, tmp_hdf5):
        from vimseo.utilities.distribution import InterfacedDistributionSettings

        settings = InterfacedDistributionSettings(
            name="Beta", parameters=(2.0, 3.0), lower_bound=0.0, upper_bound=1.0
        )

        @dataclass
        class ResultWithInterfaced(BaseResult):
            settings: InterfacedDistributionSettings | None = None

        result = ResultWithInterfaced(settings=settings)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.settings == settings

    def test_distribution_parameters_roundtrip(self, tmp_hdf5):
        from vimseo.utilities.distribution import DistributionParameters

        params = DistributionParameters(name="Normal", mu=2.1e5, sigma=1e2)

        @dataclass
        class ResultWithParams(BaseResult):
            distribution: DistributionParameters | None = None

        result = ResultWithParams(distribution=params)
        rt = roundtrip(result, tmp_hdf5)
        assert rt.distribution == params

    def test_nested_pydantic_model_roundtrip(self, tmp_hdf5):
        """A BaseModel field holding another BaseModel must not be flattened."""

        @dataclass
        class ResultWithNestedModel(BaseResult):
            outer: _OuterModel | None = None

        result = ResultWithNestedModel(
            outer=_OuterModel(name="x", inner=_InnerModel(value=3.5))
        )
        rt = roundtrip(result, tmp_hdf5)
        assert rt.outer.name == "x"
        assert isinstance(rt.outer.inner, _InnerModel)
        assert rt.outer.inner.value == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Tests — ParameterSpace / DesignSpace, via the DistributionSettings attached
# to each marginal (the concrete case that motivated this codec: "I don't see
# the Distributions serialized").
# ---------------------------------------------------------------------------


def _settings_dumps(space: ParameterSpace) -> dict[str, dict]:
    """Return, per uncertain variable, the ``model_dump()`` of its settings.

    Comparing dumps rather than the settings objects themselves sidesteps a
    pre-existing (unrelated to this codec) design choice of
    ``add_distributions_from_dict``: it always reconstructs a
    ``DistributionParameters`` instance, even when the original settings
    were a plain ``DistributionSettings`` -- the same normalization already
    happens on the deprecated JSON round-trip and in
    ``Material.update_from_parameter_space``. The two classes share the same
    fields, so comparing field values is the meaningful check.
    """
    return {
        name: space.distributions[name].marginals[0].vimseo_settings.model_dump()
        for name in space.uncertain_variables
    }


class TestParameterSpaceCodec:
    def test_uncertain_only_roundtrip(self, tmp_hdf5):
        """Several distribution kinds, including the DistributionSettings case
        that was reported as missing."""
        space = ParameterSpace()
        add_random_variable_interface(
            space, "x", DistributionSettings(name="Normal", mu=1.0, sigma=0.05)
        )
        add_random_variable_interface(
            space, "y", DistributionSettings(name="Uniform", lower=-1.0, upper=2.0)
        )
        add_random_variable_interface(
            space,
            "t",
            DistributionSettings(name="Triangular", lower=-1.0, upper=1.0, mode=0.0),
        )
        add_random_variable_interface(
            space,
            "w",
            DistributionSettings(name="Weibull", location=0.0, scale=1.0, shape=2.0),
        )
        add_random_variable_interface(
            space, "e", DistributionSettings(name="Exponential", loc=0.0, rate=1.5)
        )
        add_random_variable_interface(
            space,
            "b",
            InterfacedDistributionSettings(name="Exponential", parameters=(1.0, 0.0)),
        )

        with h5py.File(tmp_hdf5, "w") as f:
            serialize_value(f, "space", space)
            # It must be described in clear, not pickled.
            assert f["space"].attrs["__type__"] == "parameter_space"
        with h5py.File(tmp_hdf5, "r") as f:
            rt = deserialize_value(f, "space")

        assert isinstance(rt, ParameterSpace)
        assert set(rt.uncertain_variables) == set(space.uncertain_variables)
        assert _settings_dumps(rt) == _settings_dumps(space)

        # The reconstructed distributions are functional (correct parameters),
        # not just labels: sample and compare against the original.
        for name in space.uncertain_variables:
            original = space.distributions[name].marginals[0]
            rebuilt = rt.distributions[name].marginals[0]
            np.testing.assert_allclose(
                original.mean, rebuilt.mean, rtol=1e-8, atol=1e-12
            )

    def test_mixed_deterministic_and_uncertain_roundtrip(self, tmp_hdf5):
        """The real-world mixed case: Material.to_parameter_space()."""
        material = Material(
            name="m",
            material_relations=[
                MaterialRelation(
                    name="r",
                    properties=[
                        MaterialProperty(
                            name="young_modulus",
                            value=2.1e5,
                            lower_bound=1.9e5,
                            upper_bound=2.3e5,
                            distribution=DistributionParameters(
                                name="Normal", mu=2.1e5, sigma=1e2
                            ),
                        ),
                        MaterialProperty(
                            name="nu_p", value=0.3, lower_bound=0.2, upper_bound=0.4
                        ),
                    ],
                )
            ],
        )
        space = material.to_parameter_space(variable_names=["young_modulus", "nu_p"])

        with h5py.File(tmp_hdf5, "w") as f:
            serialize_value(f, "space", space)
        with h5py.File(tmp_hdf5, "r") as f:
            rt = deserialize_value(f, "space")

        assert set(rt.variable_names) == {"young_modulus", "nu_p"}
        assert rt.uncertain_variables == ["young_modulus"]
        np.testing.assert_allclose(rt.get_current_value(["nu_p"]), [0.3])
        np.testing.assert_allclose(rt.get_lower_bound("nu_p"), [0.2])
        np.testing.assert_allclose(rt.get_upper_bound("nu_p"), [0.4])
        assert _settings_dumps(rt) == _settings_dumps(space)

    def test_design_space_roundtrip(self, tmp_hdf5):
        """A plain DesignSpace (e.g. CalibrationStepResult.design_space)."""
        space = DesignSpace()
        space.add_variable(
            "a", size=2, lower_bound=-1.0, upper_bound=1.0, value=[0.1, 0.2]
        )
        space.add_variable("b", lower_bound=0.0)

        with h5py.File(tmp_hdf5, "w") as f:
            serialize_value(f, "space", space)
            assert f["space"].attrs["__type__"] == "design_space"
        with h5py.File(tmp_hdf5, "r") as f:
            rt = deserialize_value(f, "space")

        assert type(rt) is DesignSpace
        assert rt == space

    def test_variable_without_vimseo_settings_falls_back_to_pickle(self, tmp_hdf5):
        """A space built by bypassing vimseo's own API has no vimseo_settings.

        The whole space falls back to a single pickle blob (gemseo does not
        expose a public API to graft an already-built random variable back
        into a space), and it must still round-trip exactly.
        """
        space = ParameterSpace()
        space.add_random_variable("r", "OTNormalDistribution", mu=0.0, sigma=1.0)
        space.add_variable("z", value=3.0)

        with h5py.File(tmp_hdf5, "w") as f:
            serialize_value(f, "space", space)
            assert f["space"].attrs["__type__"] == "pickle"
        with h5py.File(tmp_hdf5, "r") as f:
            rt = deserialize_value(f, "space")

        assert rt == space

    def test_space_tool_result_full_roundtrip(self, tmp_hdf5):
        space = ParameterSpace()
        add_random_variable_interface(
            space, "x", DistributionSettings(name="Normal", mu=1.0, sigma=0.05)
        )
        result = SpaceToolResult(parameter_space=space)
        rt = roundtrip(result, tmp_hdf5)
        assert isinstance(rt.parameter_space, ParameterSpace)
        assert _settings_dumps(rt.parameter_space) == _settings_dumps(space)

    def test_material_result_full_roundtrip(self, tmp_hdf5):
        material = Material(
            name="m",
            material_relations=[
                MaterialRelation(
                    name="r",
                    properties=[
                        MaterialProperty(
                            name="young_modulus",
                            value=2.1e5,
                            distribution=DistributionParameters(
                                name="Normal", mu=2.1e5, sigma=1e2
                            ),
                        ),
                    ],
                )
            ],
        )
        space = material.to_parameter_space()
        result = MaterialResult(material=material, parameter_space=space)
        rt = roundtrip(result, tmp_hdf5)

        assert rt.material.name == "m"
        assert _settings_dumps(rt.parameter_space) == _settings_dumps(space)


# ---------------------------------------------------------------------------
# Tests — non-serializable objects (pickle fallback)
# ---------------------------------------------------------------------------


class _FakeObject:
    def __init__(self):
        self.value = 42


def _correlated_joint_distribution():
    correlation = ot.CorrelationMatrix(2)
    correlation[0, 1] = -0.25
    return ot.JointDistribution(
        [ot.Uniform(0.0, 3.0), ot.Uniform(1.0, 3.0)], ot.NormalCopula(correlation)
    )


def _has_pickle(group: h5py.Group) -> bool:
    """Whether an HDF5 group contains a value serialized in pickle format."""
    found = []

    def visit(_, node):
        if node.attrs.get("__type__") == "pickle":
            found.append(node)

    group.visititems(visit)
    return bool(found)


class TestOpenTurnsDistributions:
    @pytest.mark.parametrize(
        "distribution",
        [
            ot.Normal(1.0, 2.0),
            ot.Uniform(0.0, 5.0),
            ot.WeibullMin(2.0, 1.5, 0.0),
            ot.TruncatedDistribution(ot.Normal(0.0, 1.0), -1.0, 2.0),
            ot.TruncatedDistribution(
                ot.Normal(0.0, 1.0), 1.0, ot.TruncatedDistribution.LOWER
            ),
            ot.ComposedDistribution([ot.Uniform(0.0, 5.0)] * 2),
            _correlated_joint_distribution(),
        ],
    )
    def test_roundtrip_in_clear(self, tmp_hdf5, distribution):
        """A distribution is written in clear and built back identically."""
        with h5py.File(tmp_hdf5, "w") as f:
            serialize_value(f, "distribution", distribution)
        with h5py.File(tmp_hdf5, "r") as f:
            assert f["distribution"].attrs["__type__"] == "ot_distribution"
            assert not _has_pickle(f)
            rt = deserialize_value(f, "distribution")
        assert str(rt) == str(distribution)
        assert list(rt.getParameter()) == list(distribution.getParameter())

    def test_list_of_marginals(self, tmp_hdf5):
        marginals = [ot.Uniform(0.0, 5.0), ot.Normal(1.0, 2.0)]
        with h5py.File(tmp_hdf5, "w") as f:
            serialize_value(f, "marginals", marginals)
        with h5py.File(tmp_hdf5, "r") as f:
            assert not _has_pickle(f)
            rt = deserialize_value(f, "marginals")
        assert [str(m) for m in rt] == [str(m) for m in marginals]

    def test_not_describable_falls_back_to_pickle(self, tmp_hdf5):
        distribution = ot.UserDefined(ot.Sample([[0.0], [1.0], [3.0]]))
        with h5py.File(tmp_hdf5, "w") as f:
            serialize_value(f, "distribution", distribution)
        with h5py.File(tmp_hdf5, "r") as f:
            assert f["distribution"].attrs["__type__"] == "pickle"
            rt = deserialize_value(f, "distribution")
        assert str(rt) == str(distribution)

    def test_bayes_prior_in_settings(self, tmp_hdf5):
        """The prior of a Bayes analysis, stored in its settings, is in clear."""
        prior = _correlated_joint_distribution()
        result = BayesAnalysisResult()
        result.metadata.settings = {"likelihood_dist": "Normal", "prior_dist": prior}
        rt = roundtrip(result, tmp_hdf5)
        with h5py.File(tmp_hdf5, "r") as f:
            assert not _has_pickle(f["metadata"])
        assert str(rt.metadata.settings["prior_dist"]) == str(prior)


class TestPickleFallback:
    def test_custom_object_roundtrip(self, tmp_hdf5):
        """A custom non-serializable object should be pickled."""

        custom_obj = _FakeObject()

        @dataclass
        class ResultWithCustom(BaseResult):
            custom: object = None

        result = ResultWithCustom(custom=custom_obj)
        rt = roundtrip(result, tmp_hdf5)
        # On vérifie que l'objet a bien été désérialisé (pas None)
        assert rt.custom is not None


# ---------------------------------------------------------------------------
# Tests — real results
# ---------------------------------------------------------------------------


class TestFullResults:
    def test_bayes_analysis_result_full(self, tmp_hdf5):
        result = BayesAnalysisResult(
            raw_samples=np.linspace(0, 1, 100 * 3).reshape((100, 3)),  # ruff: ignore[numpy-legacy-random]
            thin_number=10,
            ndim=3,
            processed_samples=np.linspace(0, 1, 50 * 3).reshape((50, 3)),  # ruff: ignore[numpy-legacy-random]
            lppd=-12.5,
            ml=-8.3,
            posterior_predictive=None,
        )
        rt = roundtrip(result, tmp_hdf5)
        np.testing.assert_array_almost_equal(rt.raw_samples, result.raw_samples)
        assert rt.thin_number == 10
        assert rt.ndim == 3
        assert rt.lppd == pytest.approx(-12.5)
        assert rt.ml == pytest.approx(-8.3)
        assert rt.posterior_predictive is None

    def test_validation_point_result_full(self, tmp_hdf5):
        measured = pd.DataFrame({"force": [1.0, 2.0, 3.0], "disp": [0.1, 0.2, 0.3]})
        simulated = pd.DataFrame({"force": [1.1, 1.9, 3.1], "disp": [0.11, 0.19, 0.31]})
        error = pd.DataFrame({"force": [0.1, 0.1, 0.1], "disp": [0.01, 0.01, 0.01]})
        metrics = {"force": {"rmse": 0.1, "mae": 0.05}, "disp": {"rmse": 0.01}}

        result = ValidationPointResult(
            nominal_data={"temperature": 300.0, "load": np.array([1.0, 2.0])},
            measured_data=measured,
            simulated_data=simulated,
            sample_to_sample_error=error,
            integrated_metrics=metrics,
        )
        rt = roundtrip(result, tmp_hdf5)

        pd.testing.assert_frame_equal(rt.measured_data, measured)
        pd.testing.assert_frame_equal(rt.simulated_data, simulated)
        pd.testing.assert_frame_equal(rt.sample_to_sample_error, error)
        assert rt.integrated_metrics == metrics
        assert rt.nominal_data["temperature"] == pytest.approx(300.0)

    def test_validation_case_result(self, tmp_hdf5):
        element_wise = pd.DataFrame({"rmse_x": [0.1, 0.2], "rmse_y": [0.3, 0.4]})
        integrated = {"x": {"rmse": 0.15}, "y": {"rmse": 0.35}}
        result = ValidationCaseResult(
            element_wise_metrics=element_wise,
            integrated_metrics=integrated,
        )
        rt = roundtrip(result, tmp_hdf5)
        pd.testing.assert_frame_equal(rt.element_wise_metrics, element_wise)
        assert rt.integrated_metrics == integrated

    def test_statistics_result_with_ordered_dict(self, tmp_hdf5):
        od = OrderedDict([("mean", 1.0), ("std", 0.5), ("skewness", 0.1)])
        result = StatisticsResult(
            best_fitting_distributions={"x": "normal", "y": "lognormal"},
            statistics=od,
        )
        rt = roundtrip(result, tmp_hdf5)
        assert rt.best_fitting_distributions == {"x": "normal", "y": "lognormal"}
        assert dict(rt.statistics) == dict(od)


# ---------------------------------------------------------------------------
# Tests — robustness
# ---------------------------------------------------------------------------


class TestRobustness:
    def test_all_none_fields(self, tmp_hdf5):
        result = ValidationPointResult()
        rt = roundtrip(result, tmp_hdf5)
        assert rt.measured_data is None
        assert rt.simulated_data is None
        assert rt.nominal_data is None

    def test_file_created(self, tmp_hdf5):
        result = BayesAnalysisResult()
        result.to_hdf5(tmp_hdf5)
        assert Path(tmp_hdf5).exists()

    def test_class_name_stored(self, tmp_hdf5):
        import h5py

        result = BayesAnalysisResult(ndim=2)
        result.to_hdf5(tmp_hdf5)
        with h5py.File(tmp_hdf5, "r") as f:
            assert f.attrs["__class__"] == "BayesAnalysisResult"

    def test_idempotent_roundtrip(self, tmp_hdf5, tmp_path):
        """Two successive round-trips give same result."""
        result = ValidationPointResult(
            measured_data=pd.DataFrame({"a": [1.0, 2.0]}),
            integrated_metrics={"a": {"rmse": 0.1}},
        )
        path2 = str(tmp_path / "result2.h5")
        rt1 = roundtrip(result, tmp_hdf5)
        rt2 = roundtrip(rt1, path2)
        pd.testing.assert_frame_equal(rt2.measured_data, result.measured_data)
        assert rt2.integrated_metrics == result.integrated_metrics


# ---------------------------------------------------------------------------
# Tests — metadata
# ---------------------------------------------------------------------------
@dataclass
class _DataclassWithDefaults:
    """A dataclass mixing a required field and fields with defaults."""

    required: int
    with_default: int = 7
    with_factory: list = field(default_factory=list)


class TestSerializerLowLevel:
    """Directly exercise serialize_value / deserialize_value edge cases."""

    def test_numpy_integer_is_converted(self, tmp_path):
        path = tmp_path / "f.h5"
        with h5py.File(path, "w") as f:
            serialize_value(f, "i", np.int64(7))
        with h5py.File(path, "r") as f:
            value = deserialize_value(f, "i")
        assert value == 7

    def test_reserialization_overwrites_existing_key(self, tmp_path):
        path = tmp_path / "f.h5"
        df = pd.DataFrame({"a": [1.0]})
        with h5py.File(path, "w") as f:
            serialize_value(f, "d", {"x": 1})
            serialize_value(f, "d", {"x": 2})  # overwrite a dict group
            serialize_value(f, "df", df)
            serialize_value(f, "df", df)  # overwrite a dataframe group
        with h5py.File(path, "r") as f:
            assert deserialize_value(f, "d") == {"x": 2}
            pd.testing.assert_frame_equal(deserialize_value(f, "df"), df)

    def test_unpicklable_value_stored_as_none(self, tmp_path):
        path = tmp_path / "f.h5"
        with h5py.File(path, "w") as f:
            # A generator cannot be pickled and raises a TypeError.
            serialize_value(f, "gen", (i for i in range(3)))
        with h5py.File(path, "r") as f:
            assert deserialize_value(f, "gen") is None

    def test_dataframe_with_object_column(self, tmp_path):
        path = tmp_path / "f.h5"
        df = pd.DataFrame({"s": ["a", "b"], "n": [1.0, 2.0]})
        with h5py.File(path, "w") as f:
            serialize_value(f, "df", df)
        with h5py.File(path, "r") as f:
            out = deserialize_value(f, "df")
        assert list(out["s"]) == ["a", "b"]

    def test_deserialize_attr_edge_cases(self, tmp_path):
        path = tmp_path / "f.h5"
        with h5py.File(path, "w") as f:
            f.attrs["__type__p"] = "primitive"  # primitive, value missing
            f.attrs["__type__j"] = "json"
            f.attrs["j"] = json.dumps([1, 2, 3])
            f.attrs["__type__jmiss"] = "json"  # json, value missing
            f.attrs["__type__tmiss"] = "tuple"  # tuple, value missing
            bogus = f.create_group("bogus")
            bogus.attrs["__type__"] = "weird"  # unhandled type
        with h5py.File(path, "r") as f:
            assert deserialize_value(f, "p") is None
            assert deserialize_value(f, "j") == [1, 2, 3]
            assert deserialize_value(f, "jmiss") is None
            assert deserialize_value(f, "tmiss") is None
            assert deserialize_value(f, "missing_key") is None
            assert deserialize_value(f, "bogus") is None

    def test_deserialize_dataclass_unknown_class_raises(self, tmp_path):
        path = tmp_path / "f.h5"
        with h5py.File(path, "w") as f:
            group = f.create_group("dc")
            group.attrs["__type__"] = "dataclass"
            group.attrs["__class__"] = "nonexistent_module_xyz.NoClass"
        with h5py.File(path, "r") as f, pytest.raises(ImportError):
            deserialize_value(f, "dc")

    def test_deserialize_dataclass_uses_field_defaults(self, tmp_path):
        path = tmp_path / "f.h5"
        class_path = (
            f"{_DataclassWithDefaults.__module__}.{_DataclassWithDefaults.__qualname__}"
        )
        with h5py.File(path, "w") as f:
            group = f.create_group("dc")
            group.attrs["__type__"] = "dataclass"
            group.attrs["__class__"] = class_path
            # No field is stored: all values must fall back to defaults.
        with h5py.File(path, "r") as f:
            obj = deserialize_value(f, "dc")
        assert obj.required is None
        assert obj.with_default == 7
        assert obj.with_factory == []


def test_metadata(tmp_hdf5):
    """Correct metadata round-trip."""
    result = ValidationPointResult()
    metadata = ToolResultMetadata(
        generic={"a_generic_key": "a_generic_value"},
        misc={"a_misc_key": "a_misc_value"},
        settings={"a_settings_key": "a_settings_value"},
        report={"a_report_key": "a_report_value"},
        model=ModelDescription(name="a_model", load_case=LoadCase(name="a_loadcase")),
    )
    result.metadata = metadata
    rt = roundtrip(result, tmp_hdf5)
    assert_results_equal(rt, result)
