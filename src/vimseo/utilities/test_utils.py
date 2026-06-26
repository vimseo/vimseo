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
import sys

LOGGER = logging.getLogger(__name__)


def get_working_mock_command():
    """A command that works on Windows or Linux."""
    if sys.platform.startswith("win"):
        return "powershell Start-Sleep -m 50"
    return "sleep 0.05"


class SetConfig:
    def __init__(self, config, field_name, new_value):
        self._config = config
        self._field_name = field_name
        self._new_value = new_value
        self._original_value = None

    def __enter__(self):
        self._original_value = getattr(self._config, self._field_name)
        setattr(self._config, self._field_name, self._new_value)
        LOGGER.info(
            f"Replacing config field {self._config} with value {self._original_value} "
            f"by {self._new_value}."
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        LOGGER.info(
            f"Replacing back config value to {self._field_name}={self._original_value}."
        )
        setattr(self._config, self._field_name, self._original_value)
