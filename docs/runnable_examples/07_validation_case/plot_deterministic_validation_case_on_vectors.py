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
Deterministic validation case on a mock model
=============================================
"""

# %%
from __future__ import annotations

import logging

from gemseo.datasets.io_dataset import IODataset

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrame
from vimseo.tools.io.reader_file_dataframe import ReaderFileDataFrameSettings
from vimseo.tools.validation_case.validation_case import DeterministicValidationCase
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseInputs,
)
from vimseo.tools.validation_case.validation_case import (
    DeterministicValidationCaseSettings,
)

activate_logger(level=logging.INFO)

# %%
# The model to validate is created. this model contains a 1-D vector input ``x3``,
# of variable length.
model_name = "MockModelPersistent"
load_case = "LC1"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/validation_case",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/validation_case",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/validation_case/{model_name}_{load_case}.hdf",
    ),
)

# %%
# Synthetic reference data are read from a csv file.
# The input validation space contains the ``x3`` vector.
# ``x3`` has different lengths in the csv file (some boxes are left blank to
# that this component has no value.
# Once this csv data is loaded, the blank components are filled with NaNs.
reference_data = (
    ReaderFileDataFrame()
    .execute(
        settings=ReaderFileDataFrameSettings(
            file_name="reference_data_vector_different_lengths.csv",
            variable_names=["x3", "x1", "x2", "y4"],
            variable_names_to_group_names={
                "x1": IODataset.INPUT_GROUP,
                "x2": IODataset.INPUT_GROUP,
                "x3": IODataset.INPUT_GROUP,
                "y4": IODataset.OUTPUT_GROUP,
            },
            variable_names_to_n_components={
                "x3": 3,
            },
        ),
    )
    .dataset
)
print(reference_data)

# %%
# The validation case tool is created and executed.
# The only setting is that only output ``y4`` is validated.
validation = DeterministicValidationCase(
    working_directory="deterministic_validation_case"
)
validation.execute(
    inputs=DeterministicValidationCaseInputs(
        model=model, reference_data=reference_data
    ),
    settings=DeterministicValidationCaseSettings(output_names=["y4"]),
)

# %%
# The element-wise error metrics can be obtained, together with the input variables.
print(validation.result.element_wise_metrics)

# Standard validation plots can be shown. For vector inputs, each of its
# components are considered as scalar inputs. So for the input space
# ``x1`` and ``x3`` with ``x1`` a scalar, and ``x3`` a vector of length 3,
# the input variables shown in the plots are ``x1``, ``x3[0]``, ``x3[1]``, ``x3[2]``
validation.plot_results(
    validation.result, metric_name="RelativeErrorMetric", output_name="y4", show=True
)
validation.save_results()
