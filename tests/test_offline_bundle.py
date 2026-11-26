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

"""The helpers of the offline installation bundle, without building one.

Building a bundle downloads hundreds of MB; ``tools/offline_bundle/`` is run by hand.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools" / "offline_bundle"


def load(name: str):
    """Import a script of ``tools/offline_bundle`` by its path."""
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def build():
    return load("build_offline_bundle")


@pytest.fixture(scope="module")
def install():
    return load("install")


@pytest.mark.fast
@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("vimseo-0.2.0-py3-none-any.whl", ("vimseo", "0.2.0")),
        (
            "vimseo-0.1.8.dev83+g2423e43d0-py3-none-any.whl",
            ("vimseo", "0.1.8.dev83+g2423e43d0"),
        ),
        ("vimseo_abaqus-1.0.0-py3-none-any.whl", ("vimseo-abaqus", "1.0.0")),
        ("PyYAML-6.0.2-cp312-cp312-win_amd64.whl", ("pyyaml", "6.0.2")),
    ],
)
def test_name_and_version(build, file_name, expected):
    assert build.name_and_version(Path(file_name)) == expected


@pytest.mark.fast
@pytest.mark.parametrize(
    ("extras", "expected_vimseo"),
    [([], "vimseo==0.2.0"), (["mesh", "mlflow"], "vimseo[mesh,mlflow]==0.2.0")],
)
def test_root_requirements(build, extras, expected_vimseo):
    wheels = [
        Path("vimseo_abaqus-1.0.0-py3-none-any.whl"),
        Path("vimseo-0.2.0-py3-none-any.whl"),
    ]
    assert sorted(build.root_requirements(wheels, extras)) == sorted([
        expected_vimseo,
        "vimseo-abaqus==1.0.0",
    ])


@pytest.mark.fast
@pytest.mark.parametrize(
    ("python", "platform", "n_problems"),
    [
        ("3.12", "win-amd64", 0),
        ("3.11", "win-amd64", 1),
        ("3.12", "linux-x86_64", 1),
        ("3.11", "linux-x86_64", 2),
    ],
)
def test_check_target(install, python, platform, n_problems):
    bundle = {"python": "3.12", "platform": "win-amd64"}
    assert len(install.check_target(bundle, python, platform)) == n_problems


@pytest.mark.fast
def test_check_target_ignores_the_macos_version(install):
    """The macOS version of the platform is the one the interpreter was built for."""
    bundle = {"python": "3.12", "platform": "macosx-11.0-arm64"}
    assert not install.check_target(bundle, "3.12", "macosx-14.0-arm64")
    assert install.check_target(bundle, "3.12", "macosx-11.0-x86_64")
