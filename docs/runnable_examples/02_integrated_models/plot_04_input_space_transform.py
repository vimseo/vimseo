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
Patch a pre-processor to apply transformation on input variables.
=================================================================

"""

from __future__ import annotations

from gemseo.disciplines.analytic import AnalyticDiscipline
from numpy import atleast_1d

from vimseo.api import create_model
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.discipline_wrapper_component import (
    DisciplineWrapperComponent,
)

model = create_model("BendingTestAnalytical", "Cantilever")

# %%
# Define the transformations between new input variables and the existing model inputs:
input_transform = AnalyticDiscipline({"length": "lengthOverWidth*width"})

# %%
# Optionnaly, define default values for the existing model variables used
# in the transformations:
# input_transform.default_input_data.update({"lengthOverWidth": atleast_1d(1.0)})
# input_transform.default_input_data.update(
#     {"width": model.default_input_data["width"]}
# )

# %%
# Define the transformations between new output variables
# and the existing model outputs. Note that model outputs or inputs can be used:
output_transform = AnalyticDiscipline({
    "dplt_adim_at_force": "dplt_at_force_location/length"
})

# Optionnaly, define default values for the model variables
# used in the transformations:
# output_transform.default_input_data.update(
#     {"length": model.default_input_data["length"]}
# )

# %%
# The transformed space model has the following chain of components:
# [input_tranform,
# model.pre_processor, model.run_processor, model.post_processor,
# output_transform]
transformed_input_model = IntegratedModel(
    "Beam_Cantilever",
    [
        DisciplineWrapperComponent("Beam_Cantilever", input_transform),
        *list(model._chain.disciplines),
        DisciplineWrapperComponent("Beam_Cantilever", output_transform),
    ],
)

# %%
# The grammar of the transformed model is a SIMPLER grammar (no bounds or type):
print("Transformed model input grammar: ", transformed_input_model.input_grammar)
print("Transformed model output grammar: ", transformed_input_model.output_grammar)

model.cache = None
transformed_input_model.cache = None

# %%
# Execute the transformed model:
output_data = transformed_input_model.execute({
    "lengthOverWidth": atleast_1d(2.0),
    "width": atleast_1d(10.0),
})

# %%
# We show the input and output data of the transformed model:
print(transformed_input_model.get_input_data())
print(transformed_input_model.get_output_data())

# %%
# And check for correctness of the transformations:
assert (
    transformed_input_model._chain.disciplines[1].get_input_data()["length"]
    == 2 * transformed_input_model.get_input_data()["width"]
)
assert (
    output_data["dplt_adim_at_force"]
    == transformed_input_model._chain.disciplines[-2].get_output_data()[
        "dplt_at_force_location"
    ]
    / transformed_input_model._chain.disciplines[1].get_input_data()["length"]
)
