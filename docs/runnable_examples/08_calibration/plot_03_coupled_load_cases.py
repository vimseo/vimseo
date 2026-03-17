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
Usage of the model calibration for several load cases in the same step
======================================================================

Calibrate a model with coupling several load cases in a step.
"""

# %%
from __future__ import annotations

import logging

from gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings import NLOPT_COBYLA_Settings
from gemseo_calibration.calibrator import CalibrationMetricSettings
from numpy import atleast_1d

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.tools.calibration.calibration_step import CalibrationStep
from vimseo.tools.calibration.calibration_step import CalibrationStepInputs
from vimseo.tools.calibration.calibration_step import CalibrationStepSettings
from vimseo.tools.calibration.input_data import CALIBRATION_INPUT_DATA
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_parameter_space,
)

# %%
# We first define the logger level:
activate_logger(level=logging.INFO)

# %%
# We suppose that we want to calibrate a Hook's law homogeneous elastic isotropic
# material from reference data on a beam for two load cases:
# - cantilever bending
# - three point bending
# We now generate the reference data from the model used for the calibration.
# We define an input space in which the reference data are generated:
space_tool_result = SpaceToolFileIO().read(
    CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
)

# %%
# And we define a target Young modulus for the cantilever load case and
# the associated model:
model_name = "BendingTestAnalytical"
target_model_cantilever = create_model(
    model_name,
    "Cantilever",
    model_options=IntegratedModelSettings(
        directory_archive_persistency=PersistencyPolicy.DELETE_ALWAYS,
        directory_scratch_persistency=PersistencyPolicy.DELETE_ALWAYS,
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/coupled_load",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/coupled_load",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/coupled_load/target_{model_name}_Cantilever_cache.hdf",
    ),
)
target_young_modulus_cantilever = 2.2e5
target_model_cantilever.default_input_data["young_modulus"] = atleast_1d(
    target_young_modulus_cantilever
)
target_model_cantilever.cache = None
reference_dataset_cantilever = generate_reference_from_parameter_space(
    target_model_cantilever,
    space_tool_result.parameter_space,
    n_samples=6,
    as_dataset=True,
)

# %%
# We now define a different Young modulus for the three-points load case, considering
# that the material used in this test is different
# (the two reference data are subjected to material variability):
target_model_three_points = create_model(
    model_name,
    "ThreePoints",
    model_options=IntegratedModelSettings(
        directory_archive_persistency=PersistencyPolicy.DELETE_ALWAYS,
        directory_scratch_persistency=PersistencyPolicy.DELETE_ALWAYS,
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/coupled_load",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/coupled_load",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/coupled_load/target_{model_name}_ThreePoints_cache.hdf",
    ),
)
target_young_modulus_three_points = 2.3e5
target_model_three_points.default_input_data["young_modulus"] = atleast_1d(
    target_young_modulus_three_points
)
target_model_three_points.cache = None
reference_dataset_three_points = generate_reference_from_parameter_space(
    target_model_three_points,
    space_tool_result.parameter_space,
    n_samples=6,
    as_dataset=True,
)

# %%
# We now define the models used for the calibration:
model_cantilever = create_model(
    model_name,
    "Cantilever",
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/calibration_coupled",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/calibration_coupled",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/calibration_coupled/{model_name}_Cantilever_cache.hdf",
    ),
)
model_three_points = create_model(
    model_name,
    "ThreePoints",
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/calibration_coupled",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/calibration_coupled",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/calibration_coupled/{model_name}_ThreePoints_cache.hdf",
    ),
)

# %%
# We can now define a calibration step which will take into account both load cases
# to find the best compromise of Young modulus.
# The match between the posterior output data and the reference data cannot be perfect
# because we have deliberately used a different material to generate the two reference
# datasets.
# Assuming that we consider an equal weight of each load case in the calibration of
# the Young modulus, then we expect that the optimal value is the average of the two
# target values used to generate the reference data.
# Here, a relative mean square error metric is used to compute the mismatch between
# the simulated and reference data.
#
# .. note::
#
#     It is crucial to use a relative metric, which scales the simulated outputs
#     to a standard magnitude (by dividing by the reference data typically).
#     Otherwise, if the magnitude of the simulated outputs for each load case is
#     different, the optimizer will see metrics of different magnitudes in the objective
#     function, and will give more weight to the metric of greater magnitude.
#
output_name = "reaction_forces"
step = CalibrationStep(working_directory="coupled_step")
step.execute(
    inputs=CalibrationStepInputs(
        reference_data={
            "Cantilever": reference_dataset_cantilever,
            "ThreePoints": reference_dataset_three_points,
        },
    ),
    settings=CalibrationStepSettings(
        model_name={
            "Cantilever": model_cantilever,
            "ThreePoints": model_three_points,
        },
        control_outputs={output_name: CalibrationMetricSettings(measure="RelativeMSE")},
        input_names=[
            "height",
            "width",
            "imposed_dplt",
        ],
        parameter_names=["young_modulus"],
        optimizer_settings=NLOPT_COBYLA_Settings(max_iter=50),
    ),
)
step.save_results()

# %%
# For scalar metrics, a bar plot shows the agreement between
# the simulated and reference outputs. for the Cantilever load case:
figures = step.plot_results(step.result, save=False, show=True)
figures["Cantilever"][f"simulated_versus_reference_{output_name}_bars"]

# %%
# And fof the ThreePoints load case:
figures["ThreePoints"][f"simulated_versus_reference_{output_name}_bars"]

# %%
# We expect that the best compromise is the average value between the two
# young modulus, which is 2.25e5:
step.result.posterior_parameters["young_modulus"]
