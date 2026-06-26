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

from argparse import ArgumentParser
from typing import TYPE_CHECKING

import h5py

if TYPE_CHECKING:
    from pathlib import Path

parser = ArgumentParser(
    prog="cache_delete_entry",
    description="Delete an entry in a cache file.",
)
parser.add_argument("hdf_file_path", type=str)
parser.add_argument(
    "-i",
    "--entry_index",
    type=int,
    help="The index of the cache entry to delete. It is the row index of the dataset "
    "representation of the cache.",
)


def cache_delete_entry(
    file_path: Path | str,
    entry_index: int,
    node_path: str = "node",
):
    with h5py.File(file_path, "a") as f:
        del f[node_path][f"{entry_index + 1}"]


def main():
    arguments = vars(parser.parse_args())
    cache_delete_entry(
        arguments["hdf_file_path"],
        arguments["entry_index"],
    )


if __name__ == "__main__":
    main()
