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

import logging

from gemseo.core.base_factory import BaseFactory

from vimseo.analysis_nodes.base_analysis_node import BaseAnalysisNode
from vimseo.analysis_nodes.base_composite_analysis_node import BaseCompositeAnalysisNode

LOGGER = logging.getLogger(__name__)


class AnalysisNodesFactory(BaseFactory):
    """A factory to create the analysis nodes from a name or a class."""

    _CLASS = BaseAnalysisNode
    _PACKAGE_NAMES = ("vimseo.analysis_nodes",)


class CompositeAnalysisNodesFactory(AnalysisNodesFactory):
    """A factory to create the composite analysis nodes, i.e. the analyses."""

    _CLASS = BaseCompositeAnalysisNode
    _PACKAGE_NAMES = ("vimseo.analysis_nodes",)
