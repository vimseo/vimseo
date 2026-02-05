"""
A model composition that adds a post-processor to a model.
==========================================================

A new model is created by adding a post-processor to an existing model instance.
The cache of the existing model is reused while running the composed model.
"""

from __future__ import annotations

from numpy import atleast_1d

from vimseo.api import create_model
from vimseo.core.components.post.post_processor import PostProcessor

# %%
# A model is created and executed.
model = create_model("BendingTestAnalytical", "Cantilever")
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
)

# %%
# The composed model is executed. Note that the cache is reused,
# so no computation is done here. Only the new post-processing is computed.
output_data = model_with_post.execute()
print("Relative max displacement:", output_data["relative_max_dplt"])
