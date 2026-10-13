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

import pytest
from numpy import array

from vimseo.core.components.post.post_processor import PostProcessor


class _FakePostProcessor(PostProcessor):
    """A minimal PostProcessor whose ``_run`` output is set by the test."""

    auto_detect_grammar_files = False

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.output_grammar.update_from_data({"y1": array([0.0])})
        self.returned_output_data = {"y1": array([1.0]), "error_code": array([0])}

    def _run(self, input_data):
        return self.returned_output_data


def test_execute_passes_when_output_matches_grammar(tmp_wd):
    """No extra keys: execution succeeds and outputs are unaffected."""
    post = _FakePostProcessor(check_subprocess=True)
    data = post.execute()
    assert data["y1"] == 1.0


def test_execute_raises_on_extra_output_when_check_subprocess(tmp_wd):
    """An output key absent from the grammar must raise, not be silently dropped."""
    post = _FakePostProcessor(check_subprocess=True)
    post.returned_output_data = {
        "y1": array([1.0]),
        "error_code": array([0]),
        "extra_junk": array([1.0]),
    }
    with pytest.raises(ValueError, match="extra_junk"):
        post.execute()


def test_execute_warns_on_extra_output_without_check_subprocess(tmp_wd, caplog):
    """With check_subprocess=False, the extra key only logs a warning."""
    caplog.set_level(logging.WARNING)
    post = _FakePostProcessor(check_subprocess=False)
    post.returned_output_data = {
        "y1": array([1.0]),
        "error_code": array([0]),
        "extra_junk": array([1.0]),
    }
    data = post.execute()
    assert data["y1"] == 1.0
    assert "extra_junk" in caplog.text
