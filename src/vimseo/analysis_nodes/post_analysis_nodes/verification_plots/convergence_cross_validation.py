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

import plotly.graph_objects as go
from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.lines import Lines as GemseoLines
from numpy import isfinite
from numpy import vstack
from plotly.graph_objs import Figure

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.post_analysis_nodes.base_plot import Plotter
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots._constants import (
    _DOF_ABSCISSA_NAME,
)
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots._constants import (
    ELEMENT_SIZE_PRECISION,
)
from vimseo.utilities.plotting_utils import get_formatted_value

if TYPE_CHECKING:
    from vimseo.analysis_nodes.verification.verification_result import (
        SolutionVerificationResult,
    )


class ConvergenceCrossValidationPlotter(Plotter):
    """A line plot showing the output values versus the element size.

    All folds (of three values among the original four values) from the cross validation
    are superposed.
    """

    @BaseAnalysisNode._validate
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
        # The converged value at a null element size and its cross-validation band.
        # When Richardson succeeds this is the Richardson extrapolation and its MAD;
        # when Richardson fails it is the selected palliative and its cross-validated
        # MAD (the folds carry the per-fold palliative estimates instead of q_extrap).
        extrapolation = result.extrapolation
        q_converged = extrapolation.get("q_converged", extrapolation["q_extrap"])
        cv_mad = extrapolation.get(
            "q_converged_cv_mad", extrapolation.get("q_extrap_mad", 0.0)
        )
        cv_mad = cv_mad if isfinite(cv_mad) else 0.0
        method = extrapolation.get("q_converged_method", "richardson")
        fig.add_traces(
            go.Scatter(
                x=[0.0],
                y=[q_converged],
                name=f"converged ({method})",
                showlegend=True,
                mode="markers",
                line_color="chocolate",
                marker={"symbol": "square", "size": 11},
                error_y={"type": "data", "array": [2 * cv_mad]},
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
            # Extrapolate each fold to a null element size: the Richardson value
            # when available, otherwise the fold's palliative power-law-fit value.
            fold_converged = cross_validation_result[key]["q_extrap"]
            if not isfinite(fold_converged):
                fold_converged = cross_validation_result[key].get(
                    "q_converged_fit", fold_converged
                )
            fig.add_traces(
                go.Scatter(
                    x=[cross_validation_result[key]["h"][-1], 0.0],
                    y=[cross_validation_result[key]["q"][-1], fold_converged],
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
