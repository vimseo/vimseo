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

from pathlib import Path

import pytest
from gemseo.utils.directory_creator import DirectoryNamingMethod

from vimseo.analysis_nodes.mock.mock_analysis_node import MyAnalysisNode
from vimseo.analysis_nodes.mock.mock_analysis_node import MyBaseCompositeAnalysisNode


def test_composite_analysis_node_settings_and_inputs_grammars(tmp_wd):
    """Check that Inputs and Settings grammars are correctly taken into account for a
    composite analysis node."""
    analysis_node = MyBaseCompositeAnalysisNode(sub_analysis_nodes=[MyAnalysisNode()])
    assert analysis_node._option_names == ["foo", "composite_foo"]
    assert analysis_node._settings_names == ["foo", "composite_foo"]
    options = {"composite_foo": "composite_", "foo": "_"}
    analysis_node.execute(**options)
    assert analysis_node.options == options
    assert analysis_node.result.metadata.settings == {
        "composite_foo": "composite_",
        "foo": "_",
    }
    assert analysis_node._sub_analysis_nodes[
        "MyAnalysisNode"
    ].result.metadata.settings == {"foo": "_"}


@pytest.mark.parametrize(
    "analysis_node",
    [
        MyAnalysisNode(),
        MyAnalysisNode(working_directory="foo"),
        MyAnalysisNode(root_directory="bar"),
    ],
)
@pytest.mark.parametrize(
    ("working_directory_after_construction", "directory_naming_method"),
    [
        ("", None),
        ("", DirectoryNamingMethod.NUMBERED),
        (Path("my_dir"), None),
    ],
)
def test_save_composite_analysis_node_results(
    tmp_wd,
    working_directory_after_construction,
    directory_naming_method,
    analysis_node,
):
    """Check that a :class:`.BaseCompositeAnalysisNode` saves the result of each analysis node it is
    composed under the correct path."""
    if directory_naming_method:
        analysis_node = MyBaseCompositeAnalysisNode(
            sub_analysis_nodes=[analysis_node],
            directory_naming_method=directory_naming_method,
        )
    else:
        analysis_node = MyBaseCompositeAnalysisNode(sub_analysis_nodes=[analysis_node])
    if working_directory_after_construction != "":
        analysis_node.working_directory = working_directory_after_construction

    expected_filename = "MyBaseCompositeAnalysisNode"
    expected_sub_analysis_node_filename = "MyAnalysisNode"

    analysis_node.execute()
    analysis_node.save_results()

    if directory_naming_method == DirectoryNamingMethod.NUMBERED:
        assert analysis_node.working_directory.name == "1"

    assert (
        analysis_node.working_directory / f"{expected_filename}_result.hdf5"
    ).is_file()
    assert (
        analysis_node.working_directory
        / "MyAnalysisNode"
        / f"{expected_sub_analysis_node_filename}_result.hdf5"
    ).is_file()
