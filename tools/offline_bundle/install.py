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

r"""Install VIMSEO from this offline bundle, without internet access.

Run it with the Python of the environment to install into, preferably a virtual
environment::

    python -m venv env
    env\Scripts\activate         (Windows; on Linux: source env/bin/activate)
    python install.py

The other arguments are passed to ``pip install``, e.g. ``--upgrade``.

This file is copied into the bundle by ``build_offline_bundle.py``; it only uses the
standard library and pip, which every Python ships.
"""

from __future__ import annotations

import json
import subprocess
import sys
import sysconfig
from pathlib import Path

HERE = Path(__file__).resolve().parent


def os_and_arch(platform: str) -> tuple[str, str]:
    """The OS and the architecture of a ``sysconfig.get_platform()`` value.

    The macOS version in between (``macosx-11.0-arm64``) is left out: it is the
    minimum version the interpreter was built for, not a property of the machine.
    """
    parts = platform.split("-")
    return parts[0], parts[-1]


def check_target(bundle: dict[str, str], python: str, platform: str) -> list[str]:
    """The reasons why the wheels of the bundle cannot install on this Python."""
    problems = []
    if python != bundle["python"]:
        problems.append(
            f"The bundle is built for Python {bundle['python']}, "
            f"this is Python {python}."
        )
    if os_and_arch(platform) != os_and_arch(bundle["platform"]):
        problems.append(
            f"The bundle is built for {bundle['platform']}, this machine is {platform}."
        )
    return problems


def main() -> None:
    """Check that the bundle suits this Python, then install it with pip."""
    bundle = json.loads((HERE / "bundle.json").read_text(encoding="utf-8"))
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    problems = check_target(bundle, python, sysconfig.get_platform())
    if problems:
        sys.exit("\n".join([*problems, "Build a bundle for this machine."]))
    if sys.prefix == sys.base_prefix:
        print(f"Not in a virtual environment: installing into {sys.prefix}")
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-index",
        "--find-links",
        str(HERE / "wheels"),
        "--requirement",
        str(HERE / "requirements.txt"),
        *sys.argv[1:],
    ]
    sys.exit(subprocess.run(command, check=False).returncode)


if __name__ == "__main__":
    main()
