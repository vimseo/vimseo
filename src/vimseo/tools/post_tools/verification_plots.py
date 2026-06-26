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

from typing import TYPE_CHECKING

import plotly.express as px
import plotly.graph_objects as go
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.post.dataset.lines import Lines as GemseoLines
from numpy import full
from numpy import isnan
from numpy import vstack
from plotly.graph_objs import Figure

from vimseo.core.model_metadata import MetaDataNames
from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter
from vimseo.utilities.plotting_utils import get_formatted_value

if TYPE_CHECKING:
    from vimseo.tools.verification.verification_result import SolutionVerificationResult

_DOF_ABSCISSA_NAME = "N_dof_coarsest / N_dof"
ELEMENT_SIZE_PRECISION = 4


class ErrorMetricHistogram(Plotter):
    """An histogram plot where the abscissa is the error value and the ordinate the
    number of verification points corresponding to this error."""

    @BaseTool.validate
    def execute(
        self,
        element_wise_metrics: Dataset,
        metric_name: str,
        output_name: str,
        /,
        renamer=None,
        show: bool = False,
        save: bool = True,
    ):
        # Rename element-wise metrics to ensure variable names are unique.
        dataset = element_wise_metrics.copy()
        df = dataset.get_view(group_names=[IODataset.INPUT_GROUP, metric_name]).copy()
        df.columns = df.get_columns(as_tuple=False)
        output_name = output_name if not renamer else renamer(output_name, metric_name)
        fig = px.histogram(df, x=output_name)
        if save:
            fig.write_html(
                self.working_directory
                / f"metric_histogram_{metric_name}_{output_name}.html"
            )
        if show:
            fig.show()
        self.result.figure = fig


class ConvergenceCrossValidation(Plotter):
    """A line plot showing the output values versus the element size.

    All folds (of three values among the original four values) from the cross validation
    are superposed.
    """

    @BaseTool.validate
    def execute(
        self,
        result: SolutionVerificationResult,
        /,
        show: bool = False,
        save: bool = True,
    ):
        cross_validation_result = result.cross_validation

        fig = Figure()
        colors = {
            "fold_0": "blue",
            "fold_1": "red",
            "fold_2": "black",
            "fold_3": "green",
            "fold_4": "orange",
            "fold_5": "magenta",
            "fold_6": "cyan",
        }
        if result.metadata.misc["element_size_variable_name"] == "degrees_of_freedom":
            element_size_variable_name = _DOF_ABSCISSA_NAME
        else:
            element_size_variable_name = result.metadata.misc[
                "element_size_variable_name"
            ]
        output_name = result.metadata.settings["output_name"]
        fig.add_traces(
            go.Scatter(
                x=[0.0],
                y=[result.extrapolation["q_extrap"]],
                name="",
                showlegend=False,
                mode="markers",
                line_color="chocolate",
                marker={"symbol": "square"},
                error_y={
                    "type": "data",
                    "array": [2 * result.extrapolation["q_extrap_mad"]],
                },
            )
        )
        keys = list(cross_validation_result.keys())
        for key in keys:
            formatted_element_sizes = get_formatted_value(
                cross_validation_result[key]["h"], ELEMENT_SIZE_PRECISION
            )
            dataset = Dataset.from_array(
                data=vstack([
                    cross_validation_result[key]["h"],
                    cross_validation_result[key]["q"],
                ]).T,
                variable_names=[
                    element_size_variable_name,
                    f"fold{formatted_element_sizes}",
                ],
            )
            lines = GemseoLines(
                dataset, abscissa_variable=element_size_variable_name, add_markers=True
            )
            lines.color = colors[key]
            lines.linestyle = "--"
            lines.execute(
                fig=fig,
                show=False,
                save=False,
                file_format="html",
            )
            fig.add_traces(
                go.Scatter(
                    x=[cross_validation_result[key]["h"][-1], 0.0],
                    y=[
                        cross_validation_result[key]["q"][-1],
                        cross_validation_result[key]["q_extrap"],
                    ],
                    name="",
                    showlegend=False,
                    mode="lines",
                    line={"color": colors[key], "dash": "dashdot"},
                )
            )

        fig.update_layout(yaxis_title=output_name)

        if show:
            fig.show()
        if save:
            fig.write_html(
                self.working_directory / f"convergence_{output_name}_versus_h.html"
            )

        self.result.figure = fig
        return fig


class ErrorVersusElementSize(Plotter):
    """A line plot showing the error between the output values and the Richardson
    extrapolation, versus the element size."""

    def __compute_reference_lines_offset(self, y_data, x_data, cv_order, nb_meshes):
        y_ref = y_data[nb_meshes - 1]
        return (
            y_ref / x_data[nb_meshes - 1] ** cv_order
            if not isnan(y_ref)
            else 1.0 / x_data[nb_meshes - 1] ** cv_order
        )

    @BaseTool.validate
    def execute(
        self,
        result: SolutionVerificationResult,
        /,
        show: bool = False,
        save: bool = True,
    ):
        df = result.element_wise_metrics.copy()
        df.columns = result.element_wise_metrics.get_columns()
        nb_meshes = df.shape[0]
        df["median_absolute_deviation"] = full(
            (nb_meshes), result.extrapolation["q_extrap_mad"]
        )
        if result.metadata.misc["element_size_variable_name"] == "degrees_of_freedom":
            element_size_variable_name = _DOF_ABSCISSA_NAME
        else:
            element_size_variable_name = result.metadata.misc[
                "element_size_variable_name"
            ]
        output_name = result.metadata.settings["output_name"]

        fig = Figure()
        fig.add_traces(
            go.Scatter(
                x=df[element_size_variable_name],
                y=df[output_name],
                name=f"|{output_name}-extrap|",
                mode="markers",
                marker_color="blue",
            )
        )
        for cv_order, coef, color in zip(
            [1, 2],
            [
                self.__compute_reference_lines_offset(
                    df[output_name], df[element_size_variable_name], 1, nb_meshes
                ),
                self.__compute_reference_lines_offset(
                    df[output_name], df[element_size_variable_name], 2, nb_meshes
                ),
            ],
            ["green", "black"],
            strict=False,
        ):
            fig.add_traces(
                go.Scatter(
                    x=df[element_size_variable_name],
                    y=coef * df[element_size_variable_name] ** cv_order,
                    name=f"order {cv_order}",
                    mode="lines",
                    line_color=color,
                    line={"dash": "dash"},
                )
            )
        fig.update_xaxes(type="log", title=element_size_variable_name)
        fig.update_xaxes(minor={"ticks": "inside", "ticklen": 6, "showgrid": True})
        fig.update_yaxes(type="log")
        fig.update_yaxes(minor={"ticks": "inside", "ticklen": 6, "showgrid": True})
        if save:
            fig.write_html(
                self.working_directory / f"{output_name}_error_versus_h.html"
            )
        if show:
            fig.show()
        self.result.figure = fig
        return fig


class RelativeErrorVersusCpuTime(Plotter):
    """A line plot showing the relative error between the output values and the
    Richardson extrapolation, versus the element size."""

    @BaseTool.validate
    def execute(
        self,
        result: SolutionVerificationResult,
        /,
        show: bool = False,
        save: bool = True,
    ):
        df = result.simulation_and_reference.copy()
        df.columns = result.simulation_and_reference.get_columns()
        output_name = result.metadata.settings["output_name"]
        df["relative_error"] = (
            df[output_name] - result.extrapolation["q_extrap"]
        ) / result.extrapolation["q_extrap"]

        fig = Figure()
        fig.add_traces(
            go.Scatter(
                x=df[MetaDataNames.cpu_time],
                y=df["relative_error"],
                name=f"{output_name}",
                mode="lines+markers",
                marker_color="blue",
            )
        )
        fig.update_yaxes(
            title=f"Relative error on {output_name}",
            minor={"ticks": "inside", "ticklen": 6, "showgrid": True},
        )
        fig.update_xaxes(
            title=MetaDataNames.cpu_time,
            minor={"ticks": "inside", "ticklen": 6, "showgrid": True},
        )
        if save:
            fig.write_html(
                self.working_directory / f"{output_name}_error_versus_cpu_time.html"
            )
        if show:
            fig.show()
        self.result.figure = fig
        return fig


class RelativeErrorVersusElementSize(Plotter):
    r"""A line plot showing the element size versus the relative error
    :math:`\frac{q - q_{extrap}}{q_{extrap}}`."""

    @BaseTool.validate
    def execute(
        self,
        result: SolutionVerificationResult,
        /,
        show: bool = False,
        save: bool = True,
    ):
        df = result.simulation_and_reference.copy()
        df.columns = result.simulation_and_reference.get_columns()
        output_name = result.metadata.settings["output_name"]
        df["relative_error"] = (
            df[output_name] - result.extrapolation["q_extrap"]
        ) / result.extrapolation["q_extrap"]
        element_size_variable_name = result.metadata.misc["element_size_variable_name"]

        fig = Figure()
        fig.add_traces(
            go.Scatter(
                x=df[element_size_variable_name],
                y=df["relative_error"],
                name=f"{output_name}",
                mode="lines+markers",
                marker_color="blue",
            )
        )
        fig.update_yaxes(
            title=f"Relative error on {output_name}",
            minor={"ticks": "inside", "ticklen": 6, "showgrid": True},
        )
        fig.update_xaxes(
            title=f"{element_size_variable_name}",
            minor={"ticks": "inside", "ticklen": 6, "showgrid": True},
        )
        # TODO commonalize in Plotter
        if save:
            fig.write_html(
                self.working_directory / f"{output_name}_error_versus_element_size.html"
            )
        if show:
            fig.show()
        self.result.figure = fig
        return fig
