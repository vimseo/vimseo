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

"""A dashboard to visualize results from a parameter space."""

from __future__ import annotations

import tempfile
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from gemseo.algos.parameter_space import ParameterSpace
from numpy import array
from numpy import linspace
from plotly.subplots import make_subplots

from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.dashboards.visualisation.utils import st_create_model
from vimseo.material.material import Material

#: The abstract base that ``SpaceAnalysisNode`` advertises but cannot instantiate.
_ABSTRACT_SPACE_BUILDER = "SpaceBuilder"


def initialize(session_state):

    variables = {
        "model_name": "BendingTestAnalytical",
        "lc_name": "Cantilever",
        "variable_names": [],
        "space_builder_name": "FromModelCenterAndCov",
        "distribution_name": "OTTriangularDistribution",
        "working_directory": "",
        "space_analysis_node": SpaceAnalysisNode(),
    }

    for name, default in variables.items():
        if name not in session_state:
            session_state[name] = default


DEFAULT_RELATIVE_MARGIN = 0.1
"""The relative margin around the default value of a variable without bound."""


def get_default_bounds(model, bounds, sign: int) -> dict[str, float]:
    """Return the bounds of the inputs of a model, to pre-fill a form.

    Args:
        model: The model.
        bounds: The lower or upper bounds of the model.
        sign: ``-1`` for the lower bounds, ``1`` for the upper bounds.

    Returns:
        The bound of each input, or its default value plus or minus
        :data:`DEFAULT_RELATIVE_MARGIN` if it has no bound.
    """
    default_bounds = {}
    for name in model.input_grammar.names:
        if name in bounds:
            default_bounds[name] = float(bounds[name])
            continue
        try:
            default_value = float(model.default_input_data[name].ravel()[0])
        except (KeyError, TypeError, ValueError, AttributeError):
            # No numerical default value.
            default_value = 0.0
        margin = DEFAULT_RELATIVE_MARGIN * abs(default_value) or 1.0
        default_bounds[name] = default_value + sign * margin
    return default_bounds


def get_space_builder_names():
    """Return the names of the space builders that can actually be built.

    ``SpaceAnalysisNode.get_available_space_builders`` also reports ``SpaceBuilder``,
    the abstract base the concrete builders derive from. It ships no settings
    grammar, so ``SpaceBuilderFactory.create`` raises on it; offering it in the
    dashboard would break the page as soon as it is selected.
    """
    return [
        name
        for name in SpaceAnalysisNode.get_available_space_builders()
        if name != _ABSTRACT_SPACE_BUILDER
    ]


@st.cache_data
def load_parameter_space_from_file_or_material(
    _space_result,
    space_result_key,
    material_json_file,
    is_from_model_material,
    model_name,
    lc_name,
):
    """A Streamlit cached data to load a parameter space.

    The parameter space can be loaded from:
      - a ``SpaceAnalysisNodeResult``, identified in the cache by ``space_result_key``.
      - a material defined by a JSON file.
      - the material of a model.
    """
    if _space_result is not None:
        loaded_parameter_space = _space_result.parameter_space
    else:
        material = None
        if material_json_file is not None:
            temp_dir = tempfile.TemporaryDirectory()
            dir_path = Path(temp_dir.name)
            Path(dir_path / material_json_file.name).write_bytes(
                material_json_file.getvalue()
            )
            material = Material.from_json(
                dir_path=dir_path, file_name=material_json_file.name
            )
            temp_dir.cleanup()
        elif is_from_model_material:
            material = st_create_model(model_name, lc_name).material

        if material is not None:
            loaded_parameter_space = material.to_parameter_space()
        else:
            loaded_parameter_space = ParameterSpace()

    return loaded_parameter_space


def plot_marginal(marginal, variable_name: str) -> go.Figure:
    """Plot the probability and cumulative density functions of a marginal.

    Args:
        marginal: A marginal of a distribution of a ``ParameterSpace``.
        variable_name: The name of the variable, used as abscissa label.

    Returns:
        The figure, with the PDF on the primary axis and the CDF on the secondary
        one.
    """
    lower_bound = float(marginal.num_lower_bound)
    upper_bound = float(marginal.num_upper_bound)
    x_values = linspace(lower_bound, upper_bound, 200)
    sample = x_values.reshape(-1, 1)
    pdf = array(marginal.distribution.computePDF(sample)).ravel()
    cdf = array(marginal.distribution.computeCDF(sample)).ravel()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=x_values, y=pdf, name=repr(marginal)))
    fig.add_trace(
        go.Scatter(x=x_values, y=cdf, name="CDF", line={"dash": "dot"}),
        secondary_y=True,
    )
    fig.update_xaxes(title_text=variable_name)
    fig.update_yaxes(title_text="PDF", secondary_y=False)
    fig.update_yaxes(title_text="CDF", range=[0, 1], secondary_y=True)
    return fig


def plot_distributions(parameter_space, variable_names, model, show_model_bounds):
    """Show the parametric distributions in a parameter space.

    The bounds of a model can also be shown. If the distribution support exceeds the
    model bounds, the out-of-bounds region is filled with red. The numerical parameters
    of the distributions are also displayed on the right of the distribution plots.
    """
    plots = defaultdict(list)
    for variable_name in variable_names:
        d = parameter_space.distributions[variable_name]

        lower_bound = model.lower_bounds.get(variable_name, None)
        upper_bound = model.upper_bounds.get(variable_name, None)

        for marginal in d.marginals:
            fig = plot_marginal(marginal, variable_name)
            # TODO: put in gemseo.EmpiricalStatistics.plot()
            # l_b = d.num_lower_bound
            # u_b = d.num_upper_bound
            # x_values = arange(l_b, u_b, (u_b - l_b) / 1000)
            # df = DataFrame.from_dict(
            #     {
            #         "x": x_values,
            #         "samples": d.compute_samples(len(x_values)).ravel(),
            #     }
            # )
            # fig = px.histogram(df, x="samples", marginal="box")

            fig.update_layout(
                showlegend=True,
                title=f"Distribution of {variable_name}",
            )
            if lower_bound is not None:
                x0 = marginal.num_lower_bound
                if show_model_bounds:
                    fig.add_vline(
                        x=lower_bound,
                        line_width=3,
                        line_dash="dash",
                        line_color="green",
                    )
                if x0 < lower_bound:
                    fig.add_vrect(
                        x0=x0,
                        x1=lower_bound,
                        line_width=0,
                        fillcolor="red",
                        opacity=0.2,
                    )
            if upper_bound is not None:
                x0 = marginal.num_upper_bound
                if show_model_bounds:
                    fig.add_vline(
                        x=upper_bound,
                        line_width=3,
                        line_dash="dash",
                        line_color="green",
                    )
                if x0 > upper_bound:
                    fig.add_vrect(
                        x0=upper_bound,
                        x1=x0,
                        line_width=0,
                        fillcolor="red",
                        opacity=0.2,
                    )

            plots[variable_name].append(fig)

    return plots
