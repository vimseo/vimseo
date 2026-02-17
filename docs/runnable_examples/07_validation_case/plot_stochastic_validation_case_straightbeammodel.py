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
"""# How to define and run a stochastic validation case.

## Problem

I want to validate a model at several validation points and quantify the uncertainty
due to the uncertainty on the model inputs and the epistemic uncertainties on the
reference data.

Based on repeated measurements, the stochastic validation case of VIMSEO allows
to take into account the uncertainty on the reference, propagate the uncertainty
through the model and use specific metrics to take into the uncertaity on the outputs.

"""

from __future__ import annotations

import logging

from gemseo.datasets.io_dataset import IODataset

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.io.space_io import SpaceToolFileIO
from vimseo.material.material import Material
from vimseo.material_lib import MATERIAL_LIB_DIR
from vimseo.storage_management.base_storage_manager import PersistencyPolicy
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrame
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrameSettings
from vimseo.tools.validation.validation_point import StochasticValidationPoint
from vimseo.tools.validation.validation_point import StochasticValidationPointInputs
from vimseo.tools.validation.validation_point import StochasticValidationPointSettings
from vimseo.tools.validation_case.validation_case import DeterministicValidationCase
from vimseo.tools.validation_case.validation_case_result import ValidationCaseResult
from vimseo.utilities.datasets import SEP
from vimseo.utilities.generate_validation_reference import Bias
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_parameter_space,
)

activate_logger(level=logging.INFO)

# %%
# A first step is to generate uncertain reference data:
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

for mult_factor, batch in zip([1.01, 1.02, 1.03], [1, 2, 3], strict=False):
    reference_dataset_cantilever = generate_reference_from_parameter_space(
        target_model,
        SpaceToolFileIO()
        .read(file_name="bending_test_validation_input_space.json")
        .parameter_space,
        n_samples=6,
        input_names=["width", "height", "imposed_dplt"],
        output_names=["reaction_forces", "maximum_dplt"],
        outputs_to_bias={"reaction_forces": Bias(mult_factor=mult_factor)},
        additional_name_to_data={"nominal_length": 600.0, "batch": batch},
    )
    reference_dataset_cantilever.to_csv(
        f"reference_validation_bending_test_cantilever_{batch}.csv",
        sep=SEP,
        index=False,
    )
    print(f"The reference data for batch {batch}: ", reference_dataset_cantilever)

# %%
# Then the model to validate is created:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/stochastic_validation_case",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/stochastic_validation_case",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/stochastic_validation_case/{model_name}_{load_case}.hdf",
    ),
)

# %%
# Model input uncertainty are captured in the stochastic material properties,
# compatible with the model:
material = Material.from_json(MATERIAL_LIB_DIR / "Ta6v.json")
print("The stochastic material: ", material)

# %%
# All inputs to a stochastic validation are now prepared:
# the model, the reference data and the uncertain input space.
# We can define and run the three validation points corresponding to the three batches
# of reference data, and gather the results in a validation case result.
results = []
for batch, reference_data in zip(
    [1, 2, 3],
    [
        ReaderFileDataFrame()
        .execute(
            settings=ReaderFileDataFrameSettings(
                file_name=f"reference_validation_bending_test_cantilever_{batch}.csv",
                variable_names=[
                    "width",
                    "height",
                    "imposed_dplt",
                    "maximum_dplt",
                    "reaction_forces",
                    "nominal_length",
                    "batch",
                ],
                variable_names_to_group_names={
                    "width": IODataset.INPUT_GROUP,
                    "height": IODataset.INPUT_GROUP,
                    "imposed_dplt": IODataset.INPUT_GROUP,
                    "reaction_forces": IODataset.OUTPUT_GROUP,
                    "maximum_dplt": IODataset.OUTPUT_GROUP,
                },
            )
        )
        .dataset
        for batch in [1, 2, 3]
    ],
    strict=False,
):
    print(f"The reference data for batch {batch}: ", reference_data)

    result = StochasticValidationPoint().execute(
        inputs=StochasticValidationPointInputs(
            model=model,
            measured_data=reference_data,
            uncertain_input_space=material.to_parameter_space(),
        ),
        settings=StochasticValidationPointSettings(
            metric_names=[
                "AreaMetric",
                "RelativeMeanToMean",
                "AbsoluteRelativeErrorP90",
            ]
        ),
    )

    print(f"The error dataset for batch {batch}: ", result.integrated_metrics)

    results.append(result)

case_result = ValidationCaseResult()
case_result.set_from_point_results(results)
case_result

# %%
# Even if the validation case is stochastic,
# it is possible to get the same plots as for a deterministic validation case,
# using integrated metrics such as the AreaMetric (or a metric of this family),
# which output a scalar value for each validation point.
# The plots are computed for a given output and metric:
figs = DeterministicValidationCase().plot_results(
    case_result,
    metric_name="AbsoluteRelativeErrorP90",
    output_name="reaction_forces",
    show=True,
    save=False,
)
# a parallel coordinates plot:
figs["parallel_coordinates"]

# %%
# an error scatter matrix:
figs["error_scatter_matrix"]

# %%
# a predict-versus-true plot:
figs["predict_vs_true"]

# %%
# a bar plot of the integrated metrics:
figs["integrated_metric_bars"]
