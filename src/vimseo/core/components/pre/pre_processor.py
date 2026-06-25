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
from typing import ClassVar

from vimseo.core.components.external_software_component import ExternalSoftwareComponent

LOGGER = logging.getLogger(__name__)


class PreProcessor(ExternalSoftwareComponent):
    """Class defining library of components dedicated to pre-processing.

    _run method to be overloaded.
    """

    USE_JOB_DIRECTORY: ClassVar[bool] = True
    """Whether to create a job directory."""

    def __init__(self, **options) -> None:
        """
        Args:
            material_grammar_file: The ``json`` file defining the material parameters.
            material: The material.
        """
        load_case = options.pop("load_case") if "load_case" in options else None
        super().__init__(**options)
        self._load_case = load_case

    def _run(self, input_data):
        raise NotImplementedError
