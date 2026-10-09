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

"""Check that every dashboard command launches a script which opens without error.

The dashboards are discovered from the ``dashboard_*`` commands of the distribution,
so that a new dashboard is checked without writing a test.
"""

from __future__ import annotations

import pytest

from vimseo.utilities.test_utils import get_dashboard_entry_points
from vimseo.utilities.test_utils import get_dashboard_script
from vimseo.utilities.test_utils import run_dashboard

# The dashboards require the ``dashboard`` extra.
pytest.importorskip("streamlit")

ENTRY_POINTS = get_dashboard_entry_points("vimseo")


def test_dashboards_are_discovered():
    assert {entry_point.name for entry_point in ENTRY_POINTS} >= {
        "dashboard_workflow",
        "dashboard_database_viewer",
    }


@pytest.mark.fast
@pytest.mark.parametrize("entry_point", ENTRY_POINTS, ids=lambda ep: ep.name)
def test_command_launches_an_existing_script(entry_point):
    """A dashboard command launches ``streamlit run`` on an existing script."""
    script = get_dashboard_script(entry_point)
    if script is not None:
        assert script.is_file()


@pytest.mark.fast
@pytest.mark.parametrize("entry_point", ENTRY_POINTS, ids=lambda ep: ep.name)
def test_dashboard_opens(tmp_wd, entry_point):
    """The script of a dashboard command executes without error."""
    script = get_dashboard_script(entry_point)
    if script is None:
        pytest.skip(f"{entry_point.name} does not launch a Streamlit script.")
    app = run_dashboard(script)
    assert not app.exception, script
    assert not app.error, script
