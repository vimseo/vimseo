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

r"""Build a bundle to install VIMSEO on a machine without internet access.

Run it on a machine with internet access, with the OS, the processor architecture and
the Python version (major.minor) of the target machine: the bundle holds the wheels of
VIMSEO, of its plugins and of all their dependencies, built for this platform::

    python tools/offline_bundle/build_offline_bundle.py --extras mesh \
        --constraints https://github.com/vimseo/vimseo/releases/download/X.Y.Z/constraints.txt \
        git+https://forge.example.com/vims/vimseo-plugin.git@X.Y.Z

Copy the zip to the target machine, extract it and run ``python install.py`` (see the
``README.txt`` of the bundle). The target machine only needs a Python of the same
version; this script and ``install.py`` only use the standard library and pip.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from datetime import datetime
from datetime import timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

README = """\
Offline installation bundle of vimseo {vimseo}

Built for Python {python} on {platform}, on {created}.
Extras: {extras}
Plugins: {plugins}
Dependency constraints: {constraints}

On the target machine, with Python {python}, from this folder:

    python -m venv env
    env\\Scripts\\activate          (Windows)
    source env/bin/activate        (Linux, macOS)
    python install.py

install.py refuses another Python version or platform, then installs the
wheels of the folder "wheels" with pip, without accessing any package index.
"""


def pip(*args: str) -> None:
    """Run pip with the Python running this script, the one the bundle is built for."""
    command = [sys.executable, "-m", "pip", "--disable-pip-version-check", *args]
    subprocess.run(command, check=True)


def name_and_version(wheel: Path) -> tuple[str, str]:
    """The project name and the version of a wheel, from its file name.

    The wheel format escapes the ``-`` of the name into ``_``, so the name is the
    first field of the file name and the version the second.
    """
    name, version = wheel.name.split("-")[:2]
    return name.replace("_", "-").lower(), version


def root_requirements(wheels: list[Path], extras: list[str]) -> list[str]:
    """The requirements installing the given wheels at their exact version.

    ``extras`` apply to VIMSEO, whose wheel is one of ``wheels``.
    """
    requirements = []
    for wheel in sorted(wheels):
        name, version = name_and_version(wheel)
        if name == "vimseo" and extras:
            name = f"{name}[{','.join(extras)}]"
        requirements.append(f"{name}=={version}")
    return requirements


def build_roots(specs: list[str], folder: Path) -> list[Path]:
    """Build the wheels of VIMSEO and of the plugins, without their dependencies."""
    pip("wheel", "--no-deps", "--wheel-dir", str(folder), *specs)
    wheels = sorted(folder.glob("*.whl"))
    if not any(name_and_version(wheel)[0] == "vimseo" for wheel in wheels):
        msg = f"No VIMSEO wheel built from {specs[0]}"
        raise SystemExit(msg)
    return wheels


def check_bundle(bundle: Path, work: Path) -> None:
    """Install the bundle offline in a new virtual environment, as on the target."""
    env = work / "check-env"
    subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run([str(python), str(bundle / "install.py")], check=True)
    subprocess.run([str(python), "-c", "import vimseo"], check=True)


def build(
    vimseo: str,
    plugins: list[str],
    extras: list[str],
    constraints: str | None,
    output: Path,
    check: bool,
) -> Path:
    """Build the bundle folder in ``output`` and return its path."""
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    platform = sysconfig.get_platform()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        roots = build_roots([vimseo, *plugins], work / "roots")
        version = dict(map(name_and_version, roots))["vimseo"]
        name = f"vimseo-{version}-offline-{platform}-py{python.replace('.', '')}"
        bundle = output / name
        if bundle.exists():
            shutil.rmtree(bundle)
        bundle.mkdir(parents=True)
        requirements = root_requirements(roots, extras)
        plugin_requirements = [
            req for req in requirements if not req.startswith(("vimseo[", "vimseo=="))
        ]
        (bundle / "requirements.txt").write_text(
            "\n".join(requirements) + "\n", encoding="utf-8"
        )
        options = ["--constraint", constraints] if constraints else []
        pip(
            "wheel",
            "--wheel-dir",
            str(bundle / "wheels"),
            "--find-links",
            str(work / "roots"),
            *options,
            "--requirement",
            str(bundle / "requirements.txt"),
        )
        shutil.copy(HERE / "install.py", bundle)
        info = {
            "vimseo": version,
            "python": python,
            "platform": platform,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "extras": ", ".join(extras) or "none",
            "plugins": ", ".join(plugin_requirements) or "none",
            "constraints": constraints or "none",
        }
        (bundle / "bundle.json").write_text(
            json.dumps(info, indent=2) + "\n", encoding="utf-8"
        )
        (bundle / "README.txt").write_text(README.format(**info), encoding="utf-8")
        if check:
            check_bundle(bundle, work)
    return bundle


def main() -> None:
    """Parse the command line and build the bundle."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Run it with the Python version of the target machine.",
    )
    parser.add_argument(
        "plugins",
        nargs="*",
        help="The plugins to bundle, as pip requirements: a name, a path or a git URL.",
    )
    parser.add_argument(
        "--vimseo",
        default=str(ROOT),
        help="The VIMSEO to bundle, as a pip requirement, e.g. vimseo==X.Y.Z; "
        "by default the checkout holding this script.",
    )
    parser.add_argument(
        "--extras",
        default="",
        help="The extras of VIMSEO, separated by commas, e.g. mesh,mlflow.",
    )
    parser.add_argument(
        "--constraints",
        help="A pip constraints file or URL, e.g. the constraints.txt of a release, "
        "to bundle the dependency versions VIMSEO is tested with.",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="Do not install the bundle offline in a temporary environment "
        "to check that it is complete.",
    )
    parser.add_argument("--no-zip", action="store_true", help="Leave the folder only.")
    args = parser.parse_args()
    extras = [extra.strip() for extra in args.extras.split(",") if extra.strip()]
    bundle = build(
        args.vimseo,
        args.plugins,
        extras,
        args.constraints,
        args.output.resolve(),
        not args.no_check,
    )
    if not args.no_zip:
        bundle = Path(
            shutil.make_archive(
                str(bundle), "zip", root_dir=bundle.parent, base_dir=bundle.name
            )
        )
    size = sum(path.stat().st_size for path in [bundle, *bundle.rglob("*")])
    print(f"{bundle} ({size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
