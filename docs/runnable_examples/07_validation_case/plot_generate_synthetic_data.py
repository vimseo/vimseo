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

"""# Generating synthetic model output data for examples, tests or mock studies.

## Problem

As a developer, you want ot generate reference data for examples or tests, controlling
the bias of the data with respect to the model output.
As a user, you want to generate synthetic experimental data that could be used
to validate or verify a model.

## Solution

A utility function is provided to generate synthetic reference data from a model
and either:

- an input dataset or
- a parameter space to sample from.

## Example

In the example below, synthetic reference data is generated for a
bending test analytical beam model, and a bias is added to the data
to obtain non-zero error metrics in the validation case.

"""

from gemseo.datasets.io_dataset import IODataset
from numpy import atleast_1d

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.utilities.datasets import SEP
from vimseo.utilities.generate_validation_reference import Bias
from vimseo.utilities.generate_validation_reference import (
    generate_reference_from_dataset,
)

# %%
# Load a parameter space to sample from.
space_tool_result = SpaceTool.load_results("bending_test_validation_input_space.json")
print(space_tool_result)

# %%
# Generate 3 samples of input data from the parameter space,
# and create a dataset with the input data.
input_data = space_tool_result.parameter_space.compute_samples(
    n_samples=3, as_dict=False
)
reference_data = IODataset()
reference_data.add_group(
    IODataset.INPUT_GROUP,
    input_data,
    space_tool_result.parameter_space.uncertain_variables,
)

# %%
# Prepare the model and the bias to apply to the output data.
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/generate_reference_data",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/generate_reference_data",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/generate_reference_data/{model_name}_{load_case}.hdf",
    ),
)
outputs_to_bias = {"reaction_forces": Bias(mult_factor=1.05)}

# %%
# Generate the synthetic reference data from the model, the input dataset and the bias.
# Specific input data can be prescribed for some input variables,
# that are not in the input dataset,
# or that should be different from the one in the input dataset.
# The generated data can be returned as a dataset:
specific_inputs = {"length": atleast_1d(100.0)}
df = generate_reference_from_dataset(
    model,
    reference_data,
    specific_inputs=specific_inputs,
    outputs_to_bias=outputs_to_bias,
    as_dataset=True,
)
print(df)
df.to_csv("dataset_validation_beam_cantilever.csv", sep=SEP)

# Or a dataframe:
df = generate_reference_from_dataset(
    model,
    reference_data,
    specific_inputs=specific_inputs,
    outputs_to_bias=outputs_to_bias,
    as_dataset=False,
)
print(df)
df.to_csv("dataframe_validation_beam_cantilever.csv", sep=SEP)

# %%
# !!! Note
#
#    Data generation can append data to an existing dataframe,
#    but not to an existing dataset.
