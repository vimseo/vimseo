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
import pathlib

from gemseo.core.base_factory import BaseFactory

from vimseo.core.load_case import LoadCase
from vimseo.tools.post_tools.plot_parameters import PlotParameters
from vimseo.tools.post_tools.plot_parameters import create_plot

LOGGER = logging.getLogger(__name__)


class LoadCaseFactory(BaseFactory):
    """Model factory to create the Model from a name or a class."""

    _CLASS = LoadCase
    _PACKAGE_NAMES = ("vimseo.problems.load_cases",)

    def create(
        self,
        load_case_name: str,
        domain: str = "",
        **options,
    ) -> LoadCase:
        """Create a load case.

        Args:
            load_case_name: The name of the load case (its class name).
            domain: The domain of the load case.
            **options: The options of the load case.
        """
        class_name = f"{domain}_{load_case_name}" if domain != "" else load_case_name
        dummy_lc = super().create(class_name)
        json_path = dummy_lc.auto_get_file(".json", raise_error=False)

        lc_options = {}
        if json_path:
            with pathlib.Path(json_path[0]).open(encoding="utf-8") as f:
                lc_options = json.load(f)

            if "plot_parameters" in lc_options:
                plot_parameters = lc_options["plot_parameters"]
                if "curves" in plot_parameters:
                    msg = (
                        f"The plot_parameters entry curves of the JSON file of load "
                        f"case {load_case_name} has been replaced by plots: rename "
                        f"it. A list of variable names remains a valid plot "
                        f"definition, and can now hold more than one ordinate name."
                    )
                    raise ValueError(msg)
                lc_options["plot_parameters"] = PlotParameters(
                    plots=[
                        create_plot(plot) for plot in plot_parameters.get("plots", [])
                    ]
                )
        lc_options["name"] = load_case_name
        if domain != "":
            lc_options["domain"] = domain

        cls = self.get_class(class_name)
        try:
            return cls(**lc_options)
        except TypeError:
            LOGGER.exception(
                ("Failed to create class %s with keyword arguments %s."),
                class_name,
                lc_options,
            )
            raise
