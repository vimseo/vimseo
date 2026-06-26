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

import json
import pathlib


def write_failed_imports(factory_):
    (
        pathlib.Path.cwd() / f"failed_imports_{factory_.__class__.__name__}.txt"
    ).write_text(
        json.dumps(factory_.failed_imports, indent=4)
        + "\n"
        + str(factory_.class_names),
        encoding="utf-8",
    )
