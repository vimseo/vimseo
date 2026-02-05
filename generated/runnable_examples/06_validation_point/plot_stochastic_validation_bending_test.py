# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
An example of stochastic validation point
=========================================
"""

from __future__ import annotations

import logging
from pathlib import Path

from gemseo.datasets.io_dataset import IODataset
from pandas import read_csv

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.material.material import Material
from vimseo.material_lib import MATERIAL_LIB_DIR
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.tools.space.space_tool_result import SpaceToolResult
from vimseo.tools.validation.validation_point import NominalValuesOutputType
from vimseo.tools.validation.validation_point import StochasticValidationPoint
from vimseo.tools.validation.validation_point import StochasticValidationPointInputs
from vimseo.tools.validation.validation_point import StochasticValidationPointSettings
from vimseo.tools.validation.validation_point import read_nominal_values
from vimseo.utilities.datasets import SEP
from vimseo.utilities.generate_validation_reference import Bias
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_parameter_space,
)

activate_logger(level=logging.INFO)

# %%
# First we generate synthetic reference data,
# using an analytical bending test model, and bias
# the output of interest by 5 \%.
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
target_model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_persistency=PersistencyPolicy.DELETE_ALWAYS,
        directory_scratch_persistency=PersistencyPolicy.DELETE_ALWAYS,
    ),
)
target_model.cache = None
reference_dataset_cantilever = generate_reference_from_parameter_space(
    target_model,
    SpaceToolFileIO()
    .read(file_name="bending_test_validation_input_space.json")
    .parameter_space,
    n_samples=6,
    input_names=["width", "height"],
    output_names=["reaction_forces", "maximum_dplt"],
    outputs_to_bias={"reaction_forces": Bias(mult_factor=1.05)},
    additional_name_to_data={"nominal_length": 600.0, "batch": 1},
)
reference_dataset_cantilever.to_csv(
    "reference_validation_bending_test_cantilever.csv", sep=SEP
)
print("The reference data: ", reference_dataset_cantilever)

# %%
# The objective is to validate a model for a new material.
# Let's create a model to validate:
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/validation_point",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/validation_point",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/validation_point/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# And the material, which defines probability distributions for its properties.
# It is typically obtained from a calibration.
material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
print("The stochastic material: ", material)

# %%
# And the measured quantities of interest
measured_inputs = ["width", "height", "imposed_dplt"]
measured_outputs = ["reaction_forces"]

# %%
# Since reference data are referenced by batches,
# we can select a batch to perform the validation only regarding this batch:
batch = 1

# %%
# Then we define the path to the reference data
csv_path = "reference_validation_bending_test_cantilever.csv"

# %%
# and the nominal inputs
# at which the validation point is performed.
# The ``read_nominal_values`` function allows to read
# the nominal values in the reference data, using averaging
# over the repeats for a given ``master`` variable:
nominal_values = read_nominal_values(
    "batch",
    csv_path=csv_path,
    master_value=batch,
    additional_names=["nominal_length"],
    name_remapping={"nominal_length": "length"},
    output_type=NominalValuesOutputType.DICTIONARY,
)

# %%
# To speed-up the example, we coarsen the mesh:
# nominal_values.update({"element_size": atleast_1d(4.32)})

# %%
# And finally we set the nominal inputs from the material.
# Indeed, all material properties may not be stochastic
# (a distribution is not necessarily defined).
# As a result, we need to set the model default inputs
# to the deterministic property values.
# It is done through the nominal inputs:
nominal_values.update(material.get_values_as_dict())

# %%
# The reference samples are then defined from the csv file containing the measured data.
# First, the data are filtered to retain only the considered batch:
df = read_csv(
    csv_path,
    delimiter=SEP,
)
df = df[df["batch"] == batch]
df.to_csv("filtered_reference_data.csv", sep=SEP)

# %%
# Then the groups to which the measured inputs and measured QoIs belong are defined,
# and the filtered data is loaded as a GEMSEO ``Dataset``:
variable_names_to_group_names = dict.fromkeys(measured_inputs, IODataset.INPUT_GROUP)
variable_names_to_group_names.update(
    dict.fromkeys(measured_outputs, IODataset.OUTPUT_GROUP)
)
validation_dataset = IODataset.from_txt(
    "filtered_reference_data.csv",
    header=True,
    delimiter=SEP,
    variable_names_to_group_names=variable_names_to_group_names,
)

# %%
# The uncertainties coming from unmeasured inputs are then taken into account
# via the argument ``uncertain_input_space``, to which we pass a parameter
# space defined from the material.
# The stochastic validation point can now be created and executed.
# The model output uncertainty is estimated by sampling the input space
# with ``n_samples`` points.
validation_point_tool = StochasticValidationPoint(
    working_directory=Path(f"{model_name}_{load_case}")
    / f"batch_{batch}_{nominal_values['length']}",
)
validation_point_tool.execute(
    inputs=StochasticValidationPointInputs(
        model=model,
        measured_data=validation_dataset,
        uncertain_input_space=material.to_parameter_space(),
    ),
    settings=StochasticValidationPointSettings(
        metric_names=[
            "AreaMetric",
            "RelativeAreaMetric",
            "RelativeMeanToMean",
            "AbsoluteRelativeErrorP90",
        ],
        nominal_data=nominal_values,
        n_samples=4,
    ),
)

# %%
# Validation results can be saved on disk
validation_point_tool.save_results(prefix=f"batch_{batch}")

# %%
# The results can be plotted:
figures = validation_point_tool.plot_results(
    validation_point_tool.result, "reaction_forces", show=True, save=True
)

# %%
# The Q-Q plot of the measured and simulated distributions:
figures["qq_plot"]

# %%
# The comparison of the measured and simulated PDF:
figures["PDF_comparison"]

# %%
# The comparison of the measured and simulated CDF:
figures["CDF_comparison"]

# %%
# The saved result can be visualised in a dashboard by typing in a terminal
# where the vims_composites Python environment is activated:
# ``dashboard_validation_point_viewer``

# %%
# The simulated input space can be exported to disk, to be visualized with
# ``dashboard_space``.
# In pickle format:
space_tool_result = SpaceToolResult(
    parameter_space=validation_point_tool.simulated_input_space
)
space_tool_result.to_pickle("simulated_input_space")

# %%
# Or in json format:
SpaceToolFileIO().write(space_tool_result, file_base_name="simulated_input_space")
