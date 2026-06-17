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
A model composition that adds a post-processor to a model.
==========================================================

A new model is created by adding a post-processor to an existing model instance.
The cache of the existing model is reused while running the composed model.
"""

# %%
from __future__ import annotations

from numpy import atleast_1d

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.api import create_model
from vimseo.core.components.post.post_processor import PostProcessor
from vimseo.core.model_settings import IntegratedModelSettings

# %%
# A model is created and executed.
model = create_model(
    "BendingTestAnalytical",
    "Cantilever",
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/post_processing_patch",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/post_processing_patch",
        cache_file_path=EXAMPLE_RUNS_DIR
        / "caches/post_processing_patch/no_post_cache.hdf",
    ),
)
model.execute()


# %%
# Then, we want to add a post-processing, without re-running the model.
# We first create the post-processor.
class MyPost(PostProcessor):
    default_grammar_type = "SimpleGrammar"

    def __init__(self, **options):
        super().__init__(**options)
        self.input_grammar.update_from_names(
            list(model.output_grammar.names) + list(model.input_grammar.names)
        )
        self.output_grammar.update_from_data({"relative_max_dplt": atleast_1d(0.0)})

    def _run(self, input_data):
        output_data = {}
        output_data["relative_max_dplt"] = (
            input_data["dplt_at_force_location"] / input_data["length"]
        )
        return output_data


post_processor = MyPost()

# %%
# Then create a new model chaining the above model and the post-processor:
# This model is declared as a new model composition:
# ```
# class BendingTestWithPost(ModelComposition):
#     """A model composition that adds a post-processor to the bending test analytical"""
# ```
# To be discovered by the model factory, this new composed model is defined
# in the ``problems.sandbox`` subpackage. module.
model_with_post = create_model(
    "BendingTestWithPost",
    "Cantilever",
    base_model=model,
    post_components=[post_processor],
    model_options=IntegratedModelSettings(
        directory_archive_root=EXAMPLE_RUNS_DIR / "archive/post_processing_patch",
        directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/post_processing_patch",
        cache_file_path=EXAMPLE_RUNS_DIR
        / "caches/post_processing_patch/with_post_cache.hdf",
    ),
)

# %%
# The composed model is executed. Note that the cache is reused,
# so no computation is done here. Only the new post-processing is computed.
output_data = model_with_post.execute()
print("Relative max displacement:", output_data["relative_max_dplt"])

# %%
