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

import numpy as np

from vimseo.utilities.datasets import decode_vector

# DATA_DIR = Path("M:\\mat\\trust\\espace_de_travail\\SBT\\oh_study")
# vector_names = ["layup"]
# input_names = [
#     "layup",
#     "nominal_width",
#     "nominal_length",
#     "nominal_thickness",
#     "nominal_diameter",
#     "nominal_radius",
# ]
# output_names = ["max_force"]
# names_mapping = {
#     "nominal_length": "length",
#     "nominal_width": "width",
#     "nominal_thickness": "thickness",
#     "nominal_radius": "radius",
#     "nominal_diameter": "diameter",
# }
# csv_path = DATA_DIR / "prepared_X51RP1902814_v6_Coupons_Tests_Results_PartC_OHT.csv"
# output_csv_path = (
#     DATA_DIR
#     / "prepared_X51RP1902814_v6_Coupons_Tests_Results_PartC_OHT_numerical_layup.csv"
# )


def decode_stringified_vectors(ds, vector_names_to_group_names, separator: str = "_"):
    # variable_names_to_group_names = {}
    # for v in input_names:
    #     variable_names_to_group_names[v] = IODataset.INPUT_GROUP
    # for v in output_names:
    #     variable_names_to_group_names[v] = IODataset.OUTPUT_GROUP
    # ds = (
    #     ReaderFileDataFrame()
    #     .execute(
    #         settings=ReaderFileDataFrameSettings(
    #             file_name=csv_path,
    #             variable_names_to_group_names=variable_names_to_group_names,
    #         ),
    #     )
    #     .dataset
    # )
    ds = ds.get_view()  # variable_names=input_names + output_names)
    for vector_name, group_name in vector_names_to_group_names.items():
        vector_data = ds.get_view(variable_names=vector_name).to_numpy().ravel()
        numerical_vectors = [decode_vector(d, separator) for d in vector_data]
        max_length = max(len(v) for v in numerical_vectors)
        constant_length_vectors = [
            np.pad(v, (0, max_length - len(v)), mode="constant", constant_values=np.nan)
            for v in numerical_vectors
        ]

        ds.rename_variable(
            variable_name=vector_name, new_variable_name=f"{vector_name}_stringified"
        )
        ds.add_variable(
            data=constant_length_vectors,
            variable_name=vector_name,
            group_name=group_name,
        )
        # ds.rename_variable(
        #     variable_name=vector_name, new_variable_name=name_remapping[vector_name]
        # )

    return ds
