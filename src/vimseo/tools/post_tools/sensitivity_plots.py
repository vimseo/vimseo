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

import operator
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from numpy import array
from plotly.subplots import make_subplots


class SensitivityPlot(ABC):
    def __init__(self):
        self.figures = None

    @abstractmethod
    def plot(self, results, save, show, variable, indices=None, **options):
        """

        Args:
            results: A SensitivityTool result.
            title: The title of the figure to be plotted.
            **options: Specific options for the plot

        Returns:
            A figure object.
        """


class SensitivityBarPlot(SensitivityPlot):
    def __init__(self, filename="sensitivity_bar_plot"):
        super().__init__()
        self.options = {
            "filename": filename,
            "n_variables": 10,
        }

    def plot(
        self,
        results,
        save=False,
        show=True,
        output_names=(),
        indices=(),
        directory_path: str | Path = "",
        **options,
    ):
        self.options.update(options)

        indices = list(results.indices.keys()) if len(indices) == 0 else indices
        output_names = (
            results.metadata.settings["output_names"]
            if len(output_names) == 0
            else output_names
        )

        data = deepcopy(results.indices)

        self.figures = defaultdict(dict)

        for output_name in output_names:
            for index in indices:
                fig = make_subplots(
                    rows=1,
                    cols=1,
                    subplot_titles=f"Index: {index}",
                )

                input_variables = [
                    k
                    for k, v in sorted(
                        data[index][output_name][0].items(),
                        key=operator.itemgetter(1),
                    )
                ]

                color_by_variable_name = names_to_ints(input_variables)

                x = (
                    pd.DataFrame
                    .from_dict(data[index][output_name])
                    .T.sort_values(0, ascending=True)
                    .to_dict()[0]
                )
                input_variables = list(x.keys())

                if self.options["n_variables"] is not None:
                    input_variables = input_variables[0 : self.options["n_variables"]]
                    color_by_variable_name = color_by_variable_name[
                        0 : self.options["n_variables"]
                    ]
                    x = [x[k][0] for k in input_variables]

                fig.add_trace(
                    go.Bar(
                        x=x,
                        y=input_variables,
                        marker={"color": array(color_by_variable_name)},
                        orientation="h",
                    ),
                    row=1,
                    col=1,
                )

                fig.update_layout(
                    title_text=f"Sensitivity of {output_name} for index {index}"
                )
                fig.layout.title.x = 0.5
                fig.update_layout(font_size=14)
                # adjust subplot title font size.
                fig.update_annotations(font_size=12)

                if show:
                    fig.show()
                if save:
                    directory_path = (
                        Path.cwd() if directory_path == "" else Path(directory_path)
                    )
                    fig.write_html(
                        directory_path
                        / f"{self.options['filename']}_{output_name}_{index}.html"
                    )
                self.figures[output_name][index] = fig

        return self.figures


def names_to_ints(names):
    val = []
    # convert names to int
    for name in names:
        val.append(0)
        for c in name:
            val[-1] += ord(c)

    return val
