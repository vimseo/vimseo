# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This work is licensed under a BSD 0-Clause License.
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
# FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Read an experimental data as a GEMSEO Dataset
=============================================
"""

from __future__ import annotations

from pathlib import Path

from pandas import read_csv

from vimseo.api import activate_logger
from vimseo.tools.validation.validation_point import NominalValuesOutputType
from vimseo.tools.validation.validation_point import read_nominal_values
from vimseo.utilities.datasets import SEP

activate_logger()

# %%
# Loading experimental data is necessary for model validation or calibration.
# In general, the raw experimental data is not directly compatible with VIMSEO tools.
# In addition, at least two types of experimental data can be considered:
#   - a collection of validation points defined by its nominal values.
#   - a collection of validation points with repeats: the experiment
#     is repeated several times for the same nominal values. Each repeat captures
#     some variability in the material properties and some uncertainties in the
#     experimental set-up. Some input and output variables are measured for each repeat.
#
# The conversion from raw to VIMSEO-compatible data should consider the following
# requirements:
#   - conversion of data with repeats to nominal values, by considering the mean
#     value of the measured data for each validation point.
#   - presence of vectors among the measured or nominal data. For instance,
#     experiments on composites material generally define a stacking sequence
#     (layup), which is an array of ply angles. We assume that the vectors are specified
#     as strings, through an encoding procedure. Typically, ``[0.0, 5.0, 8.9]`` is
#     encoded as ``'0.0_5.0_8.9'``. NumPy string representation of array can also be used.
#
# Let's consider a non-trivial experimental data containing several validation points,
# with several repeats for each, and a vector variable ``layup``.
raw_file = Path("dummy_experimental_data.csv")
read_csv(raw_file, delimiter=SEP)

# %%
# The ``read_nominal_values`` function allows to load the raw data
# and returns nominal values.
# The ``master_name`` is the name of the variable that is used to identify the
# validation points: each validation point has the same ``master_name`` value,
# and this value is unique among the validation points.
# The ``additional_names`` are variables added to the nominal values. Their values is
# computed as the mean value of all the repeats for each validation point.
# In case the raw data names do not match the model variable names,
# a renaming can be done with ``name_remapping``.
# Finally, most VIMSEO tools use a GEMSEO Dataset as input.
# GEMSEO Datasets are multi-index column Pandas DataFrame, allowing to properly
# handle data by groups and by component (useful to handle vectors).
# Here, the nominal values are returned as a GEMSEO Dataset.
# In this case, the following additional arguments are necessary:
#  - a mapping between scalar variable names and group names, to specify in which groups
#    the variables are placed,
#  - a mapping between vector names and group names. Vectors are thus identified,
#    and are decoded as numerical arrays in the Dataset. For example,
#    ``'0.0_5.0_8.9'`` is stored as a variable having three components.
ds = read_nominal_values(
    master_name="layup",
    csv_path=raw_file,
    additional_names=[
        "nominal_width",
        "nominal_length",
        "nominal_thickness",
        "nominal_diameter",
        "nominal_radius",
        "max_force",
    ],
    name_remapping={
        "nominal_width": "width",
        "nominal_length": "length",
        "nominal_thickness": "thickness",
        "nominal_diameter": "diameter",
        "nominal_radius": "radius",
    },
    output_type=NominalValuesOutputType.GEMSEO_DATASET,
    variable_names_to_group_names={
        "layup": "inputs",
        "nominal_width": "inputs",
        "nominal_length": "inputs",
        "nominal_thickness": "inputs",
        "nominal_diameter": "inputs",
        "nominal_radius": "inputs",
        "max_force": "outputs",
    },
    vector_names_to_group_names={"layup": "inputs"},
)

# %%
# The nominal values can be exported to a csv file:
ds.to_csv(f"{raw_file.stem}_nominal_values.csv", sep=SEP)
