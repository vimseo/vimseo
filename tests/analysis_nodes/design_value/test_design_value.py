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

from vimseo.analysis_nodes.design_value import DESIGN_VALUE_LIB_DIR
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueAnalysisNode,
)
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueInputs,
)
from vimseo.analysis_nodes.design_value.design_value_analysis_node import (
    DesignValueSettings,
)
from vimseo.api import create_model
from vimseo.io.space_io import SpaceAnalysisNodeFileIO


def test_design_value(tmp_wd):

    analysis_node = DesignValueAnalysisNode()
    analysis_node.execute(
        inputs=DesignValueInputs(
            model=create_model("BendingTestAnalytical", "ThreePoints"),
            parameter_space=SpaceAnalysisNodeFileIO()
            .read(
                DESIGN_VALUE_LIB_DIR
                / "input_data"
                / "ElasticIsotropic_material_space.json"
            )
            .parameter_space,
        ),
        settings=DesignValueSettings(output_names=["reaction_forces"]),
    )
    print(analysis_node.result)
