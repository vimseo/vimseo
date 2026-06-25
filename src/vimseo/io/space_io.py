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

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import BinaryIO
from typing import TextIO

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.uncertainty.distributions.base_distribution import (
    InterfacedDistributionSettings,
)

from vimseo.io.base_tool_io import BaseToolFileIO
from vimseo.lib_vimseo.solver_utilities import EnhancedJSONEncoderModelWrapper
from vimseo.tools.space.random_variable_interface import OPTIONS_PER_DISTRIBUTION
from vimseo.tools.space.space_tool_result import SpaceToolResult
from vimseo.utilities.distribution import DistributionParameters

LOGGER = logging.getLogger(__name__)


# TODO work at more atomic level, for exmaple metadata, parameter space, dataset
#  Then the load_result, save_result methods are in charge of calling these io to
#  create the final tool result.
class SpaceToolFileIO(BaseToolFileIO):
    _EXTENSION = ".json"

    def read(
        self, file_name: str | Path, directory_path: str | Path = ""
    ) -> SpaceToolResult:
        """Read a space tool result."""

        if Path(file_name).suffix != self._EXTENSION:
            msg = f"{self.__class__.__name__} requires the file suffix to be {self._EXTENSION}."
            raise ValueError(msg)
        file_path = (
            file_name if directory_path == "" else Path(directory_path) / file_name
        )
        with Path(file_path).open() as f:
            data = json.load(f)

        result = SpaceToolResult()
        result.parameter_space = ParameterSpace()
        result.metadata = self.create_metadata(data)
        result.parameter_space = self.create_parameter_space(data)
        return result

    def read_buffer(self, buf: BinaryIO | TextIO) -> SpaceToolResult:
        """Read a space tool result."""

        data = json.loads(buf)

        result = SpaceToolResult()
        result.parameter_space = ParameterSpace()
        result.metadata = self.create_metadata(data)
        result.parameter_space = self.create_parameter_space(data)
        return result

    @classmethod
    def create_parameter_space(cls, data):
        from vimseo.tools.space.random_variable_interface import (
            add_random_variable_interface,
        )

        parameter_space = ParameterSpace()

        for variable_name, options in data["parameter_space"].items():
            # TODO bad design: the kind of distribution interface is inferred
            #  from the option keys.
            size = options.pop("size")
            if "parameters" in options and len(options["parameters"]) > 0:
                if size > 1:
                    msg = "Vector is not handled."
                    raise ValueError(msg)
                settings = InterfacedDistributionSettings(
                    name=options["name"], parameters=tuple(options["parameters"])
                )
            else:
                settings = DistributionParameters(**options)
            add_random_variable_interface(
                parameter_space,
                variable_name,
                size=size,
                settings=settings,
            )

        return parameter_space

    def _serialize_distribution_parameters(self, parameter_space: ParameterSpace):
        distribution_parameters = {}
        for variable_name, distribution in parameter_space.distributions.items():
            distribution_parameters[variable_name] = defaultdict(list)
            for marginal in distribution.marginals:
                ot_distribution_name = f"OT{marginal.settings['name']}Distribution"
                expected_keys = OPTIONS_PER_DISTRIBUTION.get(ot_distribution_name, ())
                if expected_keys == () or not set(expected_keys).issubset(
                    set(marginal.settings.keys())
                ):
                    if distribution.dimension > 1:
                        msg = (
                            f"Distribution {marginal} has the "
                            f"``InterfacedDistribution`` interface, and has dimension "
                            f"{distribution.dimension}. Only scalar variable is handled."
                        )
                        raise ValueError(msg)
                    # distribution interface is with parameters. We only handle
                    # scalar variables in this case:
                    distribution_parameters[variable_name] = marginal.settings
                else:
                    for k in expected_keys:
                        if distribution.dimension == 1:
                            distribution_parameters[variable_name][k] = (
                                marginal.settings[k]
                            )
                        else:
                            distribution_parameters[variable_name][k].append(
                                marginal.settings[k]
                            )
                    distribution_parameters[variable_name]["name"] = marginal.settings[
                        "name"
                    ]
            distribution_parameters[variable_name]["size"] = distribution.dimension

        return distribution_parameters

    def write(
        self,
        result: SpaceToolResult,
        file_base_name: str | Path = "",
        directory_path: str | Path = "",
    ) -> dict:
        data = {
            "parameter_space": self._serialize_distribution_parameters(
                result.parameter_space
            ),
            "metadata": result.metadata,
        }
        json_data = json.dumps(
            data,
            ensure_ascii=True,
            indent=4,
            cls=EnhancedJSONEncoderModelWrapper,
        )

        if file_base_name == "":
            LOGGER.warning("No base file name provided, no file is written.")
            return json_data

        if file_base_name != "":
            directory_path = (
                Path.cwd() if directory_path == "" else Path(directory_path)
            )
            file_path = directory_path / f"{file_base_name}{self._EXTENSION}"
            Path(file_path).write_text(json_data)

        return json_data
