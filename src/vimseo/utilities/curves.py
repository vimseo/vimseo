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

from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.lines import Lines
from numpy import array
from numpy import vstack
from pandas import DataFrame

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

    from numpy import ndarray
    from plotly.graph_objs import Figure


class Curve:
    """A curve."""

    __names: Iterable[str]
    __data: ndarray | None = None

    def __init__(self, data: Mapping[str, ndarray], abscissa_name=""):
        """Construct the curve from a dictionary of 1D arrays."""
        self.__names = list(data.keys())
        if len(self.__names) != 2:
            msg = (
                f"The curve should be created from a dictionary "
                f"containing exactly two items. But the dictionary "
                f"is {data}."
            )
            raise ValueError(msg)
        if abscissa_name != "":
            i = self.__names.index(abscissa_name)
            self.__names = self.__names[i:] + self.__names[:i]
            data = {name: data[name] for name in self.__names}
        self.__data = vstack(list(data.values()))
        self.__length = len(self.__data[0])

    @property
    def length(self):
        """The length of the x-axis (which is equal to the length of the y-axis)"""
        return self.__length

    @property
    def variable_names(self):
        """The (x,y) names of the variables."""
        return tuple(self.__names)

    @property
    def x(self) -> ndarray:
        return self.__data[0]

    @property
    def y(self) -> ndarray:
        return self.__data[1]

    def __update_axis_check(self, value: ndarray, axis_name: str):
        if value.ndim != 1 or len(value) != self.__length:
            msg = (
                f"{axis_name.upper()} axis should be an array of dimension 1 "
                f"and length {self.__length}."
            )
            raise ValueError(msg)

    @x.setter
    def x(self, value: ndarray):
        value = array(value)
        self.__update_axis_check(value, "X")
        self.__data[0] = value

    @y.setter
    def y(self, value: ndarray):
        value = array(value)
        self.__update_axis_check(value, "Y")
        self.__data[1] = value

    def as_dict(self):
        """The curve as a dictionary."""
        return {
            self.__names[0]: self.__data[0],
            self.__names[1]: self.__data[1],
        }

    def as_dataframe(self):
        """The curve as a ``Pandas.DataFrame``"""
        return DataFrame.from_dict(self.as_dict())

    def __str__(self):
        return self.as_dataframe().T.to_string()

    def plot(
        self,
        directory_path: str | Path = "",
        save=False,
        show=True,
        file_name: str | Path = "",
        fig: Figure | None = None,
        label: str = "",
        **options,
    ):
        """Plot the curve."""
        properties = ["color", "linestyle"]
        dataset = Dataset.from_array(
            self.__data.T,
            variable_names=self.__names,
        )
        file_name = (
            f"curve_{self.__names[1]}_vs_{self.__names[0]}.html"
            if file_name == ""
            else file_name
        )
        plot = Lines(
            dataset,
            abscissa_variable=self.__names[0],
            variables=[self.__names[1]],
        )
        if label != "":
            plot.labels = {self.__names[1]: label}
        for prop in properties:
            if prop in options:
                setattr(plot, prop, options[prop])
        return plot.execute(
            save=save,
            show=show,
            directory_path=directory_path,
            file_name=file_name,
            file_format="html",
            fig=fig,
        )[0]
