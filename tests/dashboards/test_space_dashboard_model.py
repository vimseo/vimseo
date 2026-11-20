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

from vimseo.analysis_nodes.lib.space_builder_factory import SpaceBuilderFactory
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.dashboards.space.space_dashboard_model import get_space_builder_names


def test_abstract_space_builder_is_not_offered():
    """SpaceAnalysisNode advertises its abstract base, which cannot be instantiated."""
    assert "SpaceBuilder" in SpaceAnalysisNode.get_available_space_builders()
    assert "SpaceBuilder" not in get_space_builder_names()


def test_offered_space_builders_can_be_used():
    """Every name the dashboard offers must survive what the page does with it."""
    names = get_space_builder_names()
    assert names

    for name in names:
        space_builder = SpaceBuilderFactory().create(name)
        # The page feeds this straight into the distribution selectbox.
        assert space_builder.get_available_distributions()
