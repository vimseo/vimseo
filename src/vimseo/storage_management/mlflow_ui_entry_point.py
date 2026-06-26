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

from vimseo.config.global_configuration import _configuration as config
from vimseo.storage_management.archive_settings import DEFAULT_ARCHIVE_ROOT


def main() -> None:
    if config.database.mode == "Local":
        command = [
            "mlflow",
            "ui",
            "--backend-store-uri",
            f"file:\\\\{Path(config.database.local_uri if config.database.local_uri != '' else DEFAULT_ARCHIVE_ROOT).absolute().resolve()}",
        ]
        print(f"Run command: {' '.join(command)}")
    else:
        print(f"Browse {config.database.team_uri} to open database interface.")


if __name__ == "__main__":
    main()
