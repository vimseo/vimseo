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

"""Tests of the visualization of the analysis node results."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import ClassVar

import matplotlib.pyplot as plt
import pytest
from gemseo.datasets.dataset import Dataset
from numpy import array
from pandas import DataFrame
from plotly.graph_objs import Figure
from pydantic import BaseModel
from pydantic import ValidationError

from vimseo.analysis_nodes.analysis_node_results_factory import (
    AnalysisNodeResultsFactory,
)
from vimseo.analysis_nodes.analysis_node_results_factory import load_result_buffer
from vimseo.analysis_nodes.analysis_node_results_factory import load_result_file
from vimseo.analysis_nodes.base_result import BaseResult
from vimseo.analysis_nodes.doe.doe_result import DOEResult
from vimseo.analysis_nodes.result_visualization import BasePlotSettings
from vimseo.analysis_nodes.result_visualization import fields_to_dataframes
from vimseo.analysis_nodes.result_visualization import flatten_figures
from vimseo.analysis_nodes.result_visualization import flatten_numbers
from vimseo.analysis_nodes.result_visualization import get_file_stem
from vimseo.analysis_nodes.result_visualization import mapping_to_dataframe
from vimseo.analysis_nodes.result_visualization import save_figures
from vimseo.analysis_nodes.result_visualization import show_figures
from vimseo.analysis_nodes.result_visualization import to_cell


class FakeSettings(BasePlotSettings):
    output_names: tuple[str, ...] = ()
    title: str = "title"


@dataclass
class FakeResult(BaseResult):
    """A result with a plotly and a matplotlib figure per output."""

    _PLOT_SETTINGS: ClassVar[type[FakeSettings]] = FakeSettings

    values: dict[str, float] = field(default_factory=lambda: {"a": 1.0, "b": 2.0})

    curve: list = field(default_factory=list)

    count: int = 3

    def _create_figures(self, settings):
        figures = {}
        for name in settings.output_names or tuple(self.values):
            figure, _ = plt.subplots()
            figures[name] = {
                "plotly": Figure(layout={"title": settings.title}),
                "matplotlib": figure,
            }
        return figures


@pytest.fixture
def result():
    return FakeResult()


def test_visualize_with_default_settings(result):
    """The default settings visualize everything, with flattened keys."""
    figures = result.plot()
    assert set(figures) == {
        "a_plotly",
        "a_matplotlib",
        "b_plotly",
        "b_matplotlib",
    }


def test_visualize_with_options(result):
    """The options override the settings."""
    figures = result.plot(
        settings=FakeSettings(title="foo", output_names=["a", "b"]),
        output_names=["b"],
    )
    assert set(figures) == {"b_plotly", "b_matplotlib"}
    assert figures["b_plotly"].layout.title.text == "foo"


def test_visualize_with_unknown_option(result):
    """An unknown option raises an error."""
    with pytest.raises(ValidationError):
        result.plot(foo=1)


def test_visualize_and_save(tmp_wd, result):
    """The figures are saved in files named after their keys."""
    result.plot(directory_path="figures", save=True, output_names=["a"])
    assert sorted(path.name for path in (tmp_wd / "figures").iterdir()) == [
        "a_matplotlib.png",
        "a_plotly.html",
    ]


def test_visualize_and_save_in_current_directory(tmp_wd, result):
    """Without directory, the figures are saved in the current working directory."""
    result.plot(save=True, output_names=["a"])
    assert (tmp_wd / "a_plotly.html").is_file()


def test_base_result_has_no_figure():
    """A result without visualization has no figure."""
    assert BaseResult().plot() == {}


def test_plot_family():
    """A family gives a figure of the scalars and a figure per common plot."""
    from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import Plot
    from vimseo.analysis_nodes.post_analysis_nodes.plot_parameters import Trace
    from vimseo.analysis_nodes.result_visualization import plot_family
    from vimseo.utilities.curves import CurveSet

    plot = Plot(x="x", traces=[Trace(y="y")])
    curve_sets = [
        {
            "y_vs_x": CurveSet.from_data(
                plot, {"x": array([0.0, 1.0]), "y": array([0.0, i])}
            )
        }
        for i in (2.0, 1.0)
    ]
    figures = plot_family(
        curve_sets,
        [0.4, 0.2],
        [{"force": 2.0, "label": "a"}, {"force": 1.0, "label": "b"}],
        "mesh_size",
    )
    assert set(figures) == {"scalar_outputs_vs_mesh_size", "curves_y_vs_x"}
    assert [line.name for line in figures["curves_y_vs_x"].data] == [
        "mesh_size = 0.4",
        "mesh_size = 0.2",
    ]
    assert figures["scalar_outputs_vs_mesh_size"].layout.annotations[0].text == "force"


def test_flatten_figures():
    """Nested figures are flattened, and None are ignored."""
    figure = Figure()
    assert flatten_figures({"a": {"b": figure, "c": {"d": figure}}, "e": None}) == {
        "a_b": figure,
        "a_c_d": figure,
    }


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("lc1:y", "lc1-y"),
        ("a b/c", "a-b-c"),
        ("y[0]", "y[0]"),
    ],
)
def test_get_file_stem(key, expected):
    assert get_file_stem(key) == expected


def test_save_figures(tmp_wd):
    """Plotly figures are saved in html and matplotlib figures in png."""
    figure, _ = plt.subplots()
    paths = save_figures({"x": Figure(), "y": figure}, "dir")
    assert [path.name for path in paths] == ["x.html", "y.png"]
    assert all(path.is_file() for path in paths)


def test_show_figures(monkeypatch):
    """The plotly figures are shown one by one, the matplotlib figures all at once."""
    shown = []
    monkeypatch.setattr(Figure, "show", lambda self: shown.append("plotly"))
    monkeypatch.setattr(plt, "show", lambda: shown.append("matplotlib"))
    figure, _ = plt.subplots()
    show_figures({"x": Figure(), "y": figure, "z": Figure()})
    assert shown == ["plotly", "plotly", "matplotlib"]

    shown.clear()
    show_figures({"x": Figure()})
    assert shown == ["plotly"]


def test_save_figures_as_images(tmp_wd):
    """Plotly figures are exported as images with kaleido."""
    figure, _ = plt.subplots()
    paths = save_figures({"x": Figure(), "y": figure}, "dir", file_format="svg")
    assert [path.name for path in paths] == ["x.svg", "y.svg"]
    assert all(path.stat().st_size > 0 for path in paths)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1),
        (array([2.0]), 2.0),
        (array([1.0, 2.0]), "[1.0, 2.0]"),
        (None, None),
        ("a", "a"),
    ],
)
def test_to_cell(value, expected):
    assert to_cell(value) == expected


def test_to_cell_truncates_long_texts():
    """A value which is not a number is represented by a text of limited length."""
    cell = to_cell(list(range(1000)))
    assert len(cell) == 200
    assert cell.endswith("...")


def test_mapping_to_dataframe_of_scalars():
    table = mapping_to_dataframe({"a": 1.0, "b": array([2.0])})
    assert table.to_dict() == {"value": {"a": 1.0, "b": 2.0}}


def test_mapping_to_dataframe_of_mappings():
    """A mapping of mappings gives a column per outer key."""
    table = mapping_to_dataframe({"m1": {"y1": 1.0, "y2": 2.0}, "m2": {"y1": 3.0}})
    assert list(table.columns) == ["m1", "m2"]
    assert table.loc["y1", "m2"] == pytest.approx(3.0)


def test_mapping_to_dataframe_of_arrays():
    table = mapping_to_dataframe({"a": array([1.0, 2.0]), "b": array([3.0, 4.0])})
    assert table.shape == (2, 2)


def test_mapping_to_dataframe_without_tabular_structure():
    assert mapping_to_dataframe({"a": array([1.0, 2.0]), "b": array([3.0])}) is None
    assert mapping_to_dataframe({}) is None


def test_fields_to_dataframes():
    """The tabular fields give a table and the scalar fields a table of scalars."""

    @dataclass
    class Result(BaseResult):
        dataset: Dataset = field(
            default_factory=lambda: Dataset.from_array(
                array([[1.0, 2.0]]), variable_names=["x", "y"]
            )
        )
        dataframe: DataFrame = field(default_factory=lambda: DataFrame({"z": [1]}))
        name: str = "foo"
        empty_name: str = ""
        unknown: object = field(default_factory=object)

    tables = fields_to_dataframes(Result())
    assert set(tables) == {"dataset", "dataframe", "scalars"}
    assert tables["scalars"].to_dict() == {"value": {"name": "foo"}}
    assert tables["dataset"].shape == (1, 2)


def test_tabulate_adds_the_settings(result):
    result.metadata.settings = {"n": 2, "names": ["a"]}
    tables = result.to_dataframes()
    assert set(tables) == {"values", "scalars", "settings"}
    assert tables["settings"].loc["n", "value"] == 2
    assert tables["settings"].loc["names", "value"] == "['a']"


def test_load_result_file_and_buffer(tmp_wd):
    """A result is loaded without knowing its class."""
    result = DOEResult(
        dataset=Dataset.from_array(array([[1.0, 2.0]]), variable_names=["x", "y"])
    )
    result.to_hdf5("result.hdf5")
    assert isinstance(load_result_file("result.hdf5"), DOEResult)
    content = (tmp_wd / "result.hdf5").read_bytes()
    loaded_result = load_result_buffer(content)
    assert isinstance(loaded_result, DOEResult)
    assert loaded_result.dataset.shape == (1, 2)


def test_load_result_file_with_unsupported_format(tmp_wd):
    with pytest.raises(ValueError, match=r"Unsupported file format \.pickle"):
        load_result_file("result.pickle")


@pytest.mark.parametrize("class_name", sorted(AnalysisNodeResultsFactory().class_names))
def test_visualization_settings_are_flat(class_name):
    """The settings of the visualization have default values and no nested model, so
    that a result can be visualized from a command line or a dashboard."""
    settings_class = AnalysisNodeResultsFactory().get_class(class_name)._PLOT_SETTINGS
    settings_class()
    for name, field_info in settings_class.model_fields.items():
        annotation = field_info.annotation
        assert not (
            isinstance(annotation, type) and issubclass(annotation, BaseModel)
        ), name


_NOT_SELECTING_NAMES = {
    # A label of the axis.
    ("BayesAnalysisResult", "variable_name"),
    # The convergence data are computed for a single output.
    ("SolutionVerificationCaseResult", "output_name"),
}
"""The settings named like names which do not select among names."""


@pytest.mark.parametrize("class_name", sorted(AnalysisNodeResultsFactory().class_names))
def test_plot_choices_are_given(class_name):
    """A result whose plot settings select names gives them by get_plot_choices."""
    result_class = AnalysisNodeResultsFactory().get_class(class_name)
    selecting_names = [
        name
        for name in result_class._PLOT_SETTINGS.model_fields
        if (name.endswith(("_name", "_names")) or name == "load_cases")
        and (class_name, name) not in _NOT_SELECTING_NAMES
    ]
    if selecting_names:
        assert result_class.get_plot_choices is not BaseResult.get_plot_choices


def test_flatten_numbers():
    """The finite numbers of nested mappings are flattened, arrays by component."""
    assert flatten_numbers({
        "metric": {"y1": array([1.0]), "y2": 2, "y3": float("nan")},
        "vector": array([3.0, 4.0]),
        "text": "a",
        "flag": True,
    }) == {"metric.y1": 1.0, "metric.y2": 2.0, "vector.0": 3.0, "vector.1": 4.0}


def test_base_result_has_no_key_value():
    assert BaseResult().get_key_values() == {}
