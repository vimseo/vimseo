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
Usage of the model calibration based on scalar outputs
======================================================

Calibrate a model based on scalar outputs.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from gemseo.algos.design_space import DesignSpace
from gemseo.algos.opt.multi_start.settings.multi_start_settings import (
    MultiStart_Settings,
)
from gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings import NLOPT_COBYLA_Settings
from gemseo_calibration.calibrator import CalibrationMetricSettings
from matplotlib.image import imread
from matplotlib.pyplot import imshow
from numpy import asarray
from numpy import atleast_1d

from vimseo import EXAMPLE_RUNS_DIR_NAME
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

TARGET_YOUNG_MODULUS = 2.2e5

# %%
# We first define the logger level:
activate_logger(level=logging.INFO)

# %%
# We want to calibrate an analytical model of a beam with cantilever loading made of
# a Hook's law homogeneous elastic isotropic material.
# The objective is to find the best Young modulus such that the simulated
# and reference reaction force match.

# %%
# Then, we need to create reference data.
# They are generated from the model to calibrate, which is biased by imposing a
# modified Young modulus.
# A parameter space is first created:
space_tool_result = SpaceToolFileIO().read(
    CALIBRATION_INPUT_DATA / "experimental_space_beam_cantilever.json"
)

# %%
# As well as the modified model:
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
target_model.default_input_data["young_modulus"] = atleast_1d(TARGET_YOUNG_MODULUS)
target_model.cache = None

# %%
# Six samples are generated from this model, by sampling the parameter space:
reference_dataset_cantilever = generate_reference_from_parameter_space(
    target_model, space_tool_result.parameter_space, n_samples=6, as_dataset=True
)

# %%
# We now define the model used for the calibration:
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/calibration_scalars",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/calibration_scalars",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/calibration_scalars/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# Then, a step of calibration is defined.
# Note that the model instance is passed to the ``model_name`` argument,
# since we defined the model with specific result management options.
# If we had used ``model_name = {"Cantilever": "BendingTestAnalytical"}``,
# the model would have been instantiated with its default options.
output_name = "reaction_forces"
step = CalibrationStep(working_directory="scalars_basic")
step.execute(
    inputs=CalibrationStepInputs(
        reference_data={
            "Cantilever": reference_dataset_cantilever,
        },
    ),
    settings=CalibrationStepSettings(
        model_name={"Cantilever": deepcopy(model)},
        control_outputs={
            output_name: CalibrationMetricSettings(
                measure="RelativeMSE",
            )
        },
        input_names=[
            "height",
            "width",
            "imposed_dplt",
        ],
        parameter_names=["young_modulus"],
    ),
)
step.save_results()

# %%
# We can show the prior parameters, i.e. the optimizer starting point:
step.result.prior_parameters

# %%
# Note that if argument ``starting_point`` is not specified, the prior is
# the model default inputs:
model = deepcopy(model)
model.default_input_data["young_modulus"][0]

# %%
# We can now look at the posterior parameters, i.e. the best solution found by
# the optimizer. The expected value is ``TARGET_YOUNG_MODULUS=2.2e5``:
step.result.posterior_parameters

# %%
# The convergence of the optimization can be visualized. It relies on GEMSEO
# standard plotting of optimization convergence:
imshow(asarray(imread(step.working_directory / "opt_history_view_objective.png")))

# %%
imshow(asarray(imread(step.working_directory / "opt_history_view_variables.png")))

# %%
imshow(asarray(imread(step.working_directory / "opt_history_view_x_xstar.png")))

# %%
# The effect of the calibration can also be visualized with plots comparing
# the output data before and after calibration with the reference data:
imshow(
    asarray(
        imread(
            step.working_directory
            / "simulated_versus_reference_reaction_forces_load_case_Cantilever.png"
        )
    )
)

# %%
# And specifically for scalar metrics, for each data sample (6 here),
# a bar plot shows the agreement between
# the simulated prior, posterior and reference output:
figures = step.plot_results(step.result, save=False, show=True)
figures["Cantilever"][f"simulated_versus_reference_{output_name}_bars"]

# %%
# The material before calibration:
print(model.material)

# %%
# can be updated from the posterior parameters:
calibrated_material = deepcopy(model.material)
calibrated_material.update_from_dict(step.result.posterior_parameters)
print(calibrated_material)

# %%
# A specific starting point can be prescribed:
step = CalibrationStep(working_directory="scalars_with_starting_point")
step.execute(
    inputs=CalibrationStepInputs(
        reference_data={
            "Cantilever": reference_dataset_cantilever,
        },
        starting_point={"young_modulus": 1.95e5},
    ),
    settings=CalibrationStepSettings(
        model_name={"Cantilever": deepcopy(model)},
        control_outputs={
            output_name: CalibrationMetricSettings(
                measure="RelativeMSE",
            )
        },
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
step.result.prior_parameters

# %%
# And the posterior parameters is the expected value:
step.result.posterior_parameters

# %%
# The type of optimizer and the corresponding settings can be changed.
# Note that you need to select the settings corresponding to the optimizer
# (it is not ensured automatically).
# Here, for instance, a multi-start optimization running ``NLOPT_COBYLA`` optimizer
# is chosen:
step = CalibrationStep(working_directory="scalars_specified_optimizer")
step.execute(
    inputs=CalibrationStepInputs(
        reference_data={
            "Cantilever": reference_dataset_cantilever,
        },
    ),
    settings=CalibrationStepSettings(
        model_name={"Cantilever": deepcopy(model)},
        control_outputs={
            output_name: CalibrationMetricSettings(
                measure="RelativeMSE",
            )
        },
        input_names=[
            "height",
            "width",
            "imposed_dplt",
        ],
        parameter_names=["young_modulus"],
        optimizer_name="MultiStart",
        optimizer_settings=MultiStart_Settings(
            opt_algo_name="NLOPT_COBYLA", max_iter=50
        ),
    ),
)
step.save_results()

# %%
# And the posterior parameters is the expected value:
step.result.posterior_parameters

# %%
# By default, the design space (in which the optimizer is allowed to explore)
# is defined from the model default values and bounds.
# A specific design space can be prescribed, in particular if you want to change
# its bounds.
# Note that you need to prescribe a value to argument ``value`` of method
# ``add_variable``:
design_space = DesignSpace()
design_space.add_variable(
    "young_modulus",
    value=model.default_input_data["young_modulus"][0],
    lower_bound=1.95e5,
    upper_bound=2.25e5,
)
step = CalibrationStep(working_directory="scalars_specified_design_space")
step.execute(
    inputs=CalibrationStepInputs(
        reference_data={
            "Cantilever": reference_dataset_cantilever,
        },
        design_space=design_space,
    ),
    settings=CalibrationStepSettings(
        model_name={"Cantilever": deepcopy(model)},
        control_outputs={
            output_name: CalibrationMetricSettings(
                measure="RelativeMSE",
            )
        },
        input_names=[
            "height",
            "width",
            "imposed_dplt",
        ],
        parameter_names=["young_modulus"],
        optimizer_settings=NLOPT_COBYLA_Settings(),
    ),
)
step.save_results()
step.result.posterior_parameters
