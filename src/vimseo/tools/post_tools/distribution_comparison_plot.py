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
from numpy import unique
from plotly import figure_factory
from statsmodels.distributions import ECDF

from vimseo.tools.base_tool import BaseTool
from vimseo.tools.post_tools.base_plot import Plotter

if TYPE_CHECKING:
    from vimseo.tools.validation.validation_point_result import ValidationPointResult


class DistributionComparison(Plotter):
    """Compare the simulated and reference distributions."""

    @BaseTool.validate
    def execute(
        self,
        result: ValidationPointResult,
        output_name: str,
        plot_type="CDF",
        /,
        show_type_b_uncertainties: bool = False,
        show: bool = False,
        save: bool = True,
        file_format: str = "html",
    ):
        reference_typeb_uncertainties = (
            {}
            if not result.metadata.settings["typeb_uncertainties"]
            else result.metadata.settings["typeb_uncertainties"]
        )

        simulation_uncertainties = (
            {}
            if result.metadata.report["simulated_uncertainties"] is None
            else result.metadata.report["simulated_uncertainties"]
        )

        data_ref = result.measured_data.to_dict_of_arrays(by_group=False)[
            output_name
        ].ravel()
        data_sim = result.simulated_data.to_dict_of_arrays(by_group=False)[
            output_name
        ].ravel()

        cdf_ref_type_b = False
        cdf_sim_type_b = False
        if show_type_b_uncertainties:
            if (
                reference_typeb_uncertainties
                and output_name in reference_typeb_uncertainties
            ):
                data_ref_uncertainty = reference_typeb_uncertainties[output_name]
                cdf_ref_type_b = True
            else:
                data_ref_uncertainty = 0.0
            data_ref_inf = data_ref - data_ref_uncertainty
            data_ref_sup = data_ref + data_ref_uncertainty

            if simulation_uncertainties and output_name in simulation_uncertainties:
                data_sim_uncertainty = simulation_uncertainties[output_name]
                cdf_sim_type_b = True
            else:
                data_sim_uncertainty = 0.0
            data_sim_inf = data_sim - data_sim_uncertainty
            data_sim_sup = data_sim + data_sim_uncertainty

        fig = None
        if plot_type == "PDF":
            fig = figure_factory.create_distplot(
                [data_ref, data_sim],
                group_labels=["Reference", "Simulated"],
                show_rug=False,
                show_curve=False,
                bin_size=(max(data_ref) - min(data_ref)) / data_ref.size,
            )

        elif plot_type == "CDF":
            ecdf_ref = ECDF(data_ref)
            ecdf_sim = ECDF(data_sim)

            fig = go.Figure()
            fig.add_scatter(
                mode="lines",
                x=unique(data_ref),
                y=ecdf_ref(unique(data_ref)),
                line_shape="hv",
                name="Reference",
                line_color="dodgerblue",
            )

            if cdf_ref_type_b:
                ecdf_ref_inf = ECDF(data_ref_inf)
                ecdf_ref_sup = ECDF(data_ref_sup)
                fig.add_scatter(
                    mode="lines",
                    x=unique(data_ref_inf),
                    y=ecdf_ref_inf(unique(data_ref_inf)),
                    line_shape="hv",
                    name="Reference (lower bound)",
                    line_color="steelblue",
                    line_dash="dot",
                )
                fig.add_scatter(
                    mode="lines",
                    x=unique(data_ref_sup),
                    y=ecdf_ref_sup(unique(data_ref_sup)),
                    line_shape="hv",
                    name="Reference (upper bound)",
                    line_color="darkblue",
                    line_dash="dot",
                )

            fig.add_scatter(
                mode="lines",
                x=unique(data_sim),
                y=ecdf_sim(unique(data_sim)),
                line_shape="hv",
                name="Simulated",
                line_color="red",
            )

            if cdf_sim_type_b:
                ecdf_sim_inf = ECDF(data_sim_inf)
                ecdf_sim_sup = ECDF(data_sim_sup)
                fig.add_scatter(
                    mode="lines",
                    x=unique(data_sim_inf),
                    y=ecdf_sim_inf(unique(data_sim_inf)),
                    line_shape="hv",
                    name="Simulation (lower bound)",
                    line_color="pink",
                    line_dash="dot",
                )
                fig.add_scatter(
                    mode="lines",
                    x=unique(data_sim_sup),
                    y=ecdf_sim_sup(unique(data_sim_sup)),
                    line_shape="hv",
                    name="Simulation (upper bound)",
                    line_color="darkred",
                    line_dash="dot",
                )

        fig.update_layout(
            showlegend=True,
            title=f"Empirical CDF of reference and simulated {output_name}",
        )

        if self.options["save"]:
            fig.write_html(
                self.working_directory
                / f"distribution_comparison_{plot_type}_{output_name}.html"
            )
        if self.options["show"]:
            fig.show()

        self.result.figure = fig
