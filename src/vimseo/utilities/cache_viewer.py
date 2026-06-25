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
from pathlib import Path

import pandas as pd
from gemseo.caches.hdf5_cache import HDF5Cache

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.model_metadata import MetaDataNames

parser = ArgumentParser(
    prog="cache_viewer",
    description="Inspect a cache file.",
)
parser.add_argument("hdf_file_path", type=str)
parser.add_argument(
    "-err",
    "--error_code",
    type=int,
    default=None,
    help="An integer value. The cache entries are filtered for this value of error code.",
)
var_selection = parser.add_mutually_exclusive_group()
var_selection.add_argument(
    "-scal",
    "--show_scalars_only",
    action="store_true",
    help="Whether to show only variables of dimension 1.",
)
var_selection.add_argument(
    "-monit",
    "--show_metadata_only",
    action="store_true",
    help="Whether to show only the metadata variables.",
)


def cache_viewer(
    file_path: Path | str,
    node_path: str = "",
    error_code: bool | None = None,
    show_scalars_only: bool = False,
    show_metadata_only: bool = False,
):
    """View the cache as a dataset.

    The index of the dataset does not correspond to the cache entry index. So, if a cache
    entry is removed in the middle of the cache, the dataset index and the cache entry
    index do not match anymore. It may be misleading when using the dataset index to
    remove a cache entry. You may safely remove the lastest cache entries, which do not
    cause any index mismatch.
    """
    pd.options.display.max_columns = None
    pd.options.display.max_rows = None
    pd.set_option("display.width", 200)
    pd.options.display.max_colwidth = 100

    assert (Path(file_path)).is_file()
    if node_path == "":
        cache = HDF5Cache(hdf_file_path=file_path)
    else:
        cache = HDF5Cache(hdf_file_path=file_path, hdf_node_path=node_path)

    ds = cache.to_dataset()

    if show_scalars_only:
        names = [
            name
            for name, n_dim in ds.variable_names_to_n_components.items()
            if n_dim == 1
        ]
    elif show_metadata_only:
        names = list(IntegratedModel.get_metadata_names())
    else:
        names = ds.variable_names

    # Transform to mono-index dataframe
    ds = ds.get_view(variable_names=names)
    df = ds.copy()
    df.columns = df.get_columns(as_tuple=False)

    # Shorten the job dir path
    if "job_dir" in names:
        for i, job_dir in enumerate(df["job_dir"].to_numpy()):
            job_dir_path = Path(job_dir)
            if len(job_dir_path.parts) > 1:
                df["job_dir"][i] = Path(*job_dir_path.parts[-2:])

    if error_code is None:
        print(df)
    else:
        return print(df[df[(MetaDataNames.error_code)] == f"{error_code}"])

    return df


def main():
    arguments = vars(parser.parse_args())
    cache_viewer(
        arguments["hdf_file_path"],
        node_path="",
        error_code=arguments[MetaDataNames.error_code],
        show_scalars_only=arguments["show_scalars_only"],
        show_metadata_only=arguments["show_metadata_only"],
    )


if __name__ == "__main__":
    main()
