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

import runpy
import sys
from pathlib import Path

from vimseo.utilities.optional_dependencies import import_optional


def main() -> None:
    """Launch the workflow dashboard.

    Raises:
        ImportError: If the ``dashboard`` extra is not installed.
    """
    import_optional("streamlit", "dashboard", feature="The workflow dashboard")

    import vimseo.dashboards.workflow.dashboard_workflow as dashboard

    sys.argv = [
        "streamlit",
        "run",
        str(Path(dashboard.__file__)),
    ]
    runpy.run_module("streamlit", run_name="__main__")


if __name__ == "__main__":
    main()
