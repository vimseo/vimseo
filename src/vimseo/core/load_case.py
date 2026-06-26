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

import sys
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from pathlib import Path
from typing import TYPE_CHECKING

from docstring_inheritance import GoogleDocstringInheritanceMeta
from gemseo.utils.string_tools import MultiLineString
from matplotlib.image import imread
from matplotlib.pyplot import imshow
from numpy import asarray

from vimseo.core.load import Load
from vimseo.tools.post_tools.plot_parameters import PlotParameters
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class LoadCase(metaclass=GoogleDocstringInheritanceMeta):
    """A load case."""

    name: str = ""
    """The load case name."""

    domain: str = ""
    """The domain of the load case.

    The load case class is prefixed by the domain.
    """

    summary: str = ""
    """A brief description of the load case ."""

    plot_parameters: PlotParameters = field(default_factory=PlotParameters)
    """The parameters of the plot."""

    bc_variable_names: list[str] = field(default_factory=list)
    """The names of the variables defining the boundary conditions."""

    load: Load = field(default_factory=Load)
    """The load."""

    @property
    def image_path(self):
        """The fully-qualified path to the image illustrating the load case."""
        try:
            return self.auto_get_file(".png")[0]
        except FileNotFoundError:
            return None

    def show_image(self) -> None:
        """Show the image illustrating the load case."""
        if self.image_path:
            imshow(asarray(imread(self.image_path)))

    def __post_init__(self):
        self.summary = self.__doc__ if self.summary == "" else self.summary
        self.bc_variable_names = self.get_bc_variable_names()
        self.load = self.get_load()

    def get_bc_variable_names(self) -> Iterable[str]:
        """The name of the boundary condition variables."""
        return []

    def get_plot_parameters(self) -> PlotParameters:
        return PlotParameters()

    def get_load(self) -> Load:
        return Load()

    def _get_multiline(self):
        text = MultiLineString()
        text.add(f"Load case {self.name}: {self.summary}")
        text.add("")
        text.add("Boundary condition variables:")
        text.add(str(self.bc_variable_names))
        text.add("")
        text.add("Plot parameters:")
        text.add(
            dumps(
                self.plot_parameters, sort_keys=True, indent=4, cls=EnhancedJSONEncoder
            )
        )
        text.add("Load:")
        text.add(str(self.load))
        return text

    def __str__(self):
        return str(self._get_multiline())

    def auto_get_file(
        self,
        file_suffix: str,
        raise_error=True,
    ) -> Iterable[Path]:
        """Use a naming convention to associate a verification yaml file to the model.
        Convention is {model_class_name}{file_suffix} or
        {model_class_name}_{load_case}{file_suffix}.

        Args:
            file_suffix: The suffix, including the extension, of the file to be searched
                in next to model class or its parents.
            load_cases: an iterable of load cases. If specified, only the yaml files associated
                to these load cases are returned, together with
                {model_class_name}{file_suffix}. Otherwise, all yaml files matching the
                above convention are returned.

        Returns:
            A list of file paths.
        """

        cls = self.__class__
        lc_name = cls.__name__
        classes = [cls] + [base for base in cls.__bases__ if issubclass(base, LoadCase)]
        names = [lc_name] + [cls.__name__ for cls in classes[1:]]

        matching_files = []
        for cls, name in zip(classes, names, strict=False):
            class_module = sys.modules[cls.__module__]
            directory_path = Path(class_module.__file__).parent.absolute()
            grammar_file_path = directory_path / f"{name}{file_suffix}"
            if grammar_file_path.is_file():
                matching_files.append(grammar_file_path)

        if raise_error and not matching_files:
            msg = (
                f"No files with suffix {file_suffix} were found next to "
                f"the load case {self.name} or its parent class."
            )
            raise FileNotFoundError(msg)

        return matching_files
