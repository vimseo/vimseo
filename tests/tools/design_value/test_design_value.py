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

from vimseo.api import create_model
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.tools.design_value import DESIGN_VALUE_LIB_DIR
from vimseo.tools.design_value.design_value_tool import DesignValueInputs
from vimseo.tools.design_value.design_value_tool import DesignValueSettings
from vimseo.tools.design_value.design_value_tool import DesignValueTool


def test_design_value(tmp_wd):
    # model = create_model("BendingTestAnalytical", "ThreePoints")
    # space_result = SpaceToolResult()
    # space_result.parameter_space = model.material.to_parameter_space()
    # SpaceToolFileIO().write(space_result, "ElasticIsotropic_material_space")

    tool = DesignValueTool()
    tool.execute(
        inputs=DesignValueInputs(
            model=create_model("BendingTestAnalytical", "ThreePoints"),
            parameter_space=SpaceToolFileIO()
            .read(
                DESIGN_VALUE_LIB_DIR
                / "input_data"
                / "ElasticIsotropic_material_space.json"
            )
            .parameter_space,
        ),
        settings=DesignValueSettings(output_names=["reaction_forces"]),
    )
    print(tool.result)
