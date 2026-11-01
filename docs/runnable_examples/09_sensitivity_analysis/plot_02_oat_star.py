# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
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

r"""
Local sensitivity analysis: One-factor-at-a-Time
================================================

The :class:`~.OATSensitivityAnalysisNode` measures the influence of each input of a model
around nominal values: from a center $x_0$,
each input component $i$ varies alone by a physical step $h_i$,
the other ones remaining at the center.
The points of this Design of Experiments (DOE) form a star:

```text
              x0 + h2.e2
                  |
x0 - h1.e1 ----- x0 ----- x0 + h1.e1
                  |
              x0 - h2.e2
```

Contrary to the Morris method, whose trajectories accumulate the variations,
all the effects are measured around the same point,
whatever the order of the inputs.
This analysis is cheap ($2d+1$ evaluations for $d$ input components)
but local: it does not explore the whole parameter space.
"""

# %%
# Import the packages
# -------------------
from __future__ import annotations

import logging

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.analysis_nodes.doe.doe import DOEAnalysisNode
from vimseo.analysis_nodes.doe.doe import DOEInputs
from vimseo.analysis_nodes.doe.doe import DOESettings
from vimseo.analysis_nodes.sensitivity.oat_sensitivity import OATSensitivityAnalysisNode
from vimseo.analysis_nodes.sensitivity.oat_sensitivity import OATSensitivityInputs
from vimseo.analysis_nodes.sensitivity.oat_sensitivity import OATSensitivitySettings
from vimseo.analysis_nodes.space.space_analysis_node import SpaceAnalysisNode
from vimseo.api import activate_logger
from vimseo.api import create_model
from vimseo.core.model_settings import IntegratedModelSettings

activate_logger(level=logging.INFO)

# %%
# Analysis definition
# -------------------
# Let's instantiate a model:
model_name = "BendingTestAnalytical"
load_case = "Cantilever"
model = create_model(
    model_name,
    load_case,
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/oat_sensitivity",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/oat_sensitivity",
        cache_file_path=EXAMPLE_RUNS_DIR
        / f"caches/oat_sensitivity/{model_name}_{load_case}_cache.hdf",
    ),
)

# %%
# Create a parameter space
# ------------------------
# The parameter space is built around the default values of the model,
# as in the Morris example.
# Its random variables are centered on these values,
# which are therefore the default center of the star.
space_analysis_node = SpaceAnalysisNode(working_directory="SpaceAnalysisNode_results")
retained_variables = model.get_input_data_names()
retained_variables.remove("relative_dplt_location")
space_analysis_node.execute(
    distribution_name="OTTriangularDistribution",
    space_builder_name="FromModelCenterAndCov",
    variable_names=retained_variables,
    use_default_values_as_center=True,
    model=model,
    cov=0.05,
)
space_analysis_node.execute(
    distribution_name="OTTriangularDistribution",
    space_builder_name="FromCenterAndCov",
    center_values={"relative_dplt_location": 0.9},
    cov=0.05,
)
print(space_analysis_node.parameter_space)

# %%
# Using the OATSensitivityAnalysisNode
# ----------------------------
# The analysis node executes the star DOE (DOE algorithm ``"StarDOE"``) on the model.
# The settings of the star are:
#
# - ``center``: the physical values of the center, by input name;
#   an input missing from this mapping takes its current value in the parameter
#   space, i.e. the mean of its distribution for a random variable,
# - ``relative_step``: the relative step $\delta$;
#   the step of a component is $\delta|x_{0,i}|$.
#   If the center is zero, the step is $\delta\sigma_i$ for a random variable,
#   $\delta$ times the range of the bounds if both are defined,
#   and ``fallback_step`` otherwise.
#   With a relative step, the indices do not depend on the magnitude of the inputs.
#   An input whose center is zero gets a step that is not relative to its center,
#   so its indices are not comparable with those of the others
#   (a warning is logged),
# - ``two_sided``: whether to vary each component on both sides of the center
#   (default) or only on the positive side ($d+1$ evaluations).
#
# Contrary to the ``OATDOE`` of GEMSEO,
# whose step is defined in probability for a random variable,
# the step is physical, whatever the distribution of the input.
#
# The star must remain inside the bounds of the parameter space,
# otherwise an error is raised.
# Here, the triangular distributions span $\pm 5\%$ around their mode,
# so the relative step is set to $2\%$.
# The center of ``height`` is moved from its default value 40 to 41.
output_names = ["reaction_forces", "dplt_at_force_location", "maximum_dplt"]
analysis_node = OATSensitivityAnalysisNode(working_directory="oat_sensitivity_results")
analysis_node.execute(
    inputs=OATSensitivityInputs(
        model=model, parameter_space=space_analysis_node.parameter_space
    ),
    settings=OATSensitivitySettings(
        output_names=output_names, center={"height": 41.0}, relative_step=0.02
    ),
)
analysis_node.save_results()
print(analysis_node.result)

# %%
# The inputs are ranked by decreasing absolute centered variation ``delta_f``.
# The reaction force of the cantilever is proportional to
# $h^3/(r L)^3$, where $h$ is the ``height``, $L$ the ``length``
# and $r$ the ``relative_dplt_location``:
# for the same relative step, these three inputs are equally influential
# to first order, hence their nearly equal ``delta_f``.

# %%
# The indices are, for each output and input component:
#
# - ``delta_f_plus`` and ``delta_f_minus``: the variations of the output
#   from the center, when the input increases and decreases by its step,
# - ``delta_f``: the centered variation $(f^+-f^-)/2$,
# - ``relative_delta_f``: ``delta_f`` relative to the output at the center,
# - ``gradient``: the centered finite-difference estimation of the derivative.
#
# They can be tabulated:
analysis_node.result.get_indices_dataframe("relative_delta_f")

# %%
# The tornado diagram of an output shows its variations
# from the center of the star, the most influential inputs at the top:
figures = analysis_node.result.plot(output_names=["reaction_forces"])
figures["tornado_reaction_forces"]

# %%
# Using the samples of a star DOE prepared in advance
# ---------------------------------------------------
# The star DOE can also be executed beforehand by a :class:`~.DOEAnalysisNode`
# with the DOE algorithm ``"StarDOE"``, whose settings are passed through
# ``algo_settings``.
# Here, a one-sided star.
doe_analysis_node = DOEAnalysisNode(working_directory="star_doe_results")
doe_analysis_node.execute(
    inputs=DOEInputs(model=model, parameter_space=space_analysis_node.parameter_space),
    settings=DOESettings(
        output_names=output_names,
        algo="StarDOE",
        algo_settings={
            "center": {"height": 41.0},
            "relative_step": 0.02,
            "two_sided": False,
        },
    ),
)
doe_analysis_node.result.dataset

# %%
# Its result is passed to the :class:`~.OATSensitivityAnalysisNode` as ``doe_result``:
# the model is not executed again.
# This result records the DOE algorithm, which the analysis node checks,
# and its settings, from which the analysis node reads whether the star is two-sided.
analysis_node = OATSensitivityAnalysisNode(working_directory="oat_from_doe_results")
analysis_node.execute(inputs=OATSensitivityInputs(doe_result=doe_analysis_node.result))
analysis_node.result.get_indices_dataframe("gradient")
