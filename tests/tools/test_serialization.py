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

"""Tests for BaseResult HDF5 serialization/deserialization."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset

from vimseo.core.load_case import LoadCase
from vimseo.core.model_description import ModelDescription
from vimseo.tools.base_result import BaseResult
from vimseo.tools.base_result import assert_results_equal
from vimseo.tools.bayes.bayes_analysis_result import BayesAnalysisResult
from vimseo.tools.metadata import ToolResultMetadata
from vimseo.tools.sensitivity.sensitivity_result import SensitivityResult
from vimseo.tools.statistics.statistics_result import StatisticsResult
from vimseo.tools.validation.validation_point_result import ValidationPointResult
from vimseo.tools.validation_case.validation_case_result import ValidationCaseResult
from vimseo.utilities.datasets import assert_frame_equal_unordered


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
        rt = roundtrip(result, "result.hdf5")
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
        arr = np.linspace(0,4, 40).reshape((10,4))
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
# Tests — non-serializable objects (pickle fallback)
# ---------------------------------------------------------------------------


class _FakeObject:
    def __init__(self):
        self.value = 42


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
            raw_samples=np.random.rand(100, 3),  # noqa: NPY002
            thin_number=10,
            ndim=3,
            processed_samples=np.random.rand(50, 3),  # noqa: NPY002
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
