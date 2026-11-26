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

"""The models declared in the YAML files of the ``models_path`` setting.

The directories of ``models_path`` (``VIMSEO_MODELS_PATH``) are separated by the path
separator of the system. Each YAML file declaring a model becomes a class of this
module, found by the model factory. See :mod:`vimseo.core.declarative_model`.
"""

from __future__ import annotations

import os
import sys

from vimseo.config.global_configuration import _configuration as config
from vimseo.core.declarative_model import register_declared_models

register_declared_models(
    sys.modules[__name__],
    [directory for directory in config.models_path.split(os.pathsep) if directory],
)
