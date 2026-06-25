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

from typing import TYPE_CHECKING

from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.job_executor.base_executor import JobExecutor
from vimseo.job_executor.base_user_job_options import BaseUserJobSettings

if TYPE_CHECKING:
    from vimseo.core.components.subroutines.subroutine_wrapper import SubroutineWrapper


class RunProcessor(ExternalSoftwareComponent):
    """Class defining library of components dedicated to running models.

    _run method to be overloaded.
    """

    subroutine_list: list[SubroutineWrapper]
    """A list of subroutines."""

    def __init__(self, **options):
        """
        Args:
            material: The material.
        """
        super().__init__(**options)
        self.subroutine_list = []
        self._job_executor = JobExecutor("")
        self._user_job_options = BaseUserJobSettings()

    @property
    def n_cpus(self):
        """The number of CPUs used to run the external software."""
        return self._job_executor.options["n_cpus"]
