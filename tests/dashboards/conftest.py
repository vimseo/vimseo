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

"""The fixtures of the tests of the dashboards.

The dashboards require the ``dashboard`` extra: without it, their tests are not
collected, since their modules import ``streamlit``.
"""

from __future__ import annotations

from importlib.util import find_spec

import pytest

if find_spec("streamlit") is None:
    collect_ignore_glob = ["test_*.py"]
else:

    @pytest.fixture(autouse=True)
    def clear_streamlit_caches():
        """Clear the caches of Streamlit, shared by the tests of a process.

        Otherwise, a result loaded from a relative path by a test is returned to the
        next test loading another result from the same relative path, in its own
        working directory.
        """
        import streamlit as st

        st.cache_data.clear()
        st.cache_resource.clear()
        yield
        st.cache_data.clear()
        st.cache_resource.clear()
