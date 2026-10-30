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
from numpy import isfinite
from numpy import linspace
from plotly.graph_objs import Figure

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.post_analysis_nodes.base_plot import Plotter
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots._constants import (
    _DOF_ABSCISSA_NAME,
)

if TYPE_CHECKING:
    from vimseo.analysis_nodes.verification.verification_result import (
        SolutionVerificationResult,
    )


class ConvergenceFitPlotter(Plotter):
    """A line plot of the output versus the element size, gathering every estimate of
    the converged value at a null element size.

    It overlays, when available:

    - the reference (literature) **Richardson** extrapolation;
    - the **power-law fit** palliative (least-squares ``q_conv + C h^p`` over all
      grids, with its fitted order and RMS residual);
    - the model-free **robust median** palliative (median of the finest grids with
      its uncertainty band).

    Unlike the Richardson-based plots, it stays informative when the three-point
    Richardson extrapolation fails (``nan``). The title states which estimate the
    analysis node selected as the converged value and flags explicitly when a palliative was
    used instead of Richardson.
    """

    @BaseAnalysisNode._validate
    def execute(
        self,
        result: SolutionVerificationResult,
        /,
        show: bool = False,
        save: bool = True,
    ):
        df = result.simulation_and_reference.copy()
        df.columns = result.simulation_and_reference.get_columns()
        if result.metadata.misc["element_size_variable_name"] == "degrees_of_freedom":
            element_size_variable_name = _DOF_ABSCISSA_NAME
        else:
            element_size_variable_name = result.metadata.misc[
                "element_size_variable_name"
            ]
        output_name = result.metadata.settings["output_name"]
        extrapolation = result.extrapolation

        element_sizes = df[element_size_variable_name].to_numpy()
        outputs = df[output_name].to_numpy()

        fig = Figure()
        fig.add_traces(
            go.Scatter(
                x=element_sizes,
                y=outputs,
                name=output_name,
                mode="lines+markers",
                marker_color="blue",
            )
        )

        # Reference (literature) Richardson extrapolation, if it could be computed.
        q_extrap = extrapolation.get("q_extrap")
        if q_extrap is not None and isfinite(q_extrap):
            fig.add_traces(
                go.Scatter(
                    x=[0.0],
                    y=[q_extrap],
                    name="Richardson extrapolation",
                    mode="markers",
                    marker={"color": "red", "symbol": "circle", "size": 11},
                    error_y={
                        "type": "data",
                        "array": [2.0 * extrapolation.get("q_extrap_mad", 0.0)],
                    },
                )
            )

        # Palliative 1: least-squares power-law fit q_converged + C * h^order.
        q_converged_fit = extrapolation.get("q_converged_fit")
        order_fit = extrapolation.get("order_fit")
        coefficient_fit = extrapolation.get("fit_coefficient")
        if (
            q_converged_fit is not None
            and isfinite(q_converged_fit)
            and isfinite(order_fit)
        ):
            dense_sizes = linspace(0.0, float(element_sizes.max()), 100)
            fig.add_traces(
                go.Scatter(
                    x=dense_sizes,
                    y=q_converged_fit + coefficient_fit * dense_sizes**order_fit,
                    name=(
                        f"power-law fit palliative (order={order_fit:.2f}, "
                        f"rmse={extrapolation['fit_rmse']:.2g})"
                    ),
                    mode="lines",
                    line={"color": "green", "dash": "dash"},
                )
            )
            fig.add_traces(
                go.Scatter(
                    x=[0.0],
                    y=[q_converged_fit],
                    name="q converged (power-law fit)",
                    mode="markers",
                    marker={"color": "green", "symbol": "square", "size": 10},
                )
            )

        # Palliative 2: model-free finest-grid median with its uncertainty band.
        q_converged_robust = extrapolation.get("q_converged_robust")
        band = extrapolation.get("q_converged_robust_band")
        if q_converged_robust is not None and isfinite(q_converged_robust):
            fig.add_traces(
                go.Scatter(
                    x=[0.0],
                    y=[q_converged_robust],
                    name="q converged (robust median)",
                    mode="markers",
                    marker={"color": "chocolate", "symbol": "diamond", "size": 10},
                    error_y={"type": "data", "array": [band]},
                )
            )

        # State the selected converged value and, crucially, whether it is the
        # reference Richardson method or a palliative substituted for it.
        q_converged = extrapolation.get("q_converged")
        method = extrapolation.get("q_converged_method", "")
        if q_converged is not None and isfinite(q_converged):
            title = f"Converged {output_name} = {q_converged:.4g}  (method: {method})"
        else:
            title = f"Convergence of {output_name}"
        fig.update_layout(title=title)
        fig.update_xaxes(title=element_size_variable_name)
        fig.update_yaxes(title=output_name)
        if save:
            fig.write_html(
                self.working_directory / f"convergence_fit_{output_name}.html"
            )
        if show:
            fig.show()
        self.result.figure = fig
        return fig
