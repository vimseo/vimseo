# Copyright (c) 2019 IRT-AESE.
# All rights reserved.
#
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#        :author: XXXXXXXXXXX
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
Deterministic validation case on the bending test analytical beam model against an analytical solution
======================================================================================================
"""

from __future__ import annotations

import logging

from vimseo import EXAMPLE_RUNS_DIR_NAME
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.problems.beam_analytic.reference_dataset_builder import (
    bending_test_analytical_reference_dataset,
)
from vimseo.tools.validation_case.validation_case import DeterministicValidationCase
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseInputs,
)
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseSettings,
)

activate_logger(level=logging.INFO)

# %%
# First a model is created:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/archive/validation_case",
        directory_scratch_root=f"../../../{EXAMPLE_RUNS_DIR_NAME}/scratch/validation_case",
        cache_file_path=f"../../../{EXAMPLE_RUNS_DIR_NAME}/caches/validation_case/{model_name}_{load_case}.hdf",
    ),
)

# %%
# The samples are set from synthetic reference data already generated for this model,
# to which a bias is added to obtain non-zero error metrics.
reference_data = bending_test_analytical_reference_dataset(shift=10.0)["Cantilever"]
print("The measured data: ", reference_data)


# %%
# Then, the validation case tool is created and executed:
validation_tool = DeterministicValidationCase()
results = validation_tool.execute(
    inputs=DeterministicValidationCaseInputs(
        model=model,
        reference_data=reference_data,
    ),
    settings=DeterministicValidationCaseSettings(
        metric_names=[
            "RelativeErrorMetric",
            "AbsoluteErrorMetric",
        ],
        output_names=["reaction_forces"],
    ),
)
validation_tool.save_results()

# %%
# Post-processing the results.
#
# The validation result contains:
#
#   - a dictionary mapping the error metric names,
#     output names and the statistical metric values (by default, the mean is used).
#   - a dataset containing the element-wise error metrics, together with the
#   - the simulated data, reference data and the input samples.

print("The validation result: ", validation_tool.result)
print(validation_tool.result.element_wise_metrics)
print(validation_tool.result.integrated_metrics)

# %%
# Validation results can be visualized as:
figs = validation_tool.plot_results(
    validation_tool.result,
    "RelativeErrorMetric",
    "reaction_forces",
    save=False,
    show=True,
)

# %%
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
