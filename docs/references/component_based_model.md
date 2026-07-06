<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Components of a model {#components_of_model}

The following scheme represents the concept of a model and its
components:

![Components_of_a_model](../images/model_components.png){ align=center }

In VIMSEO, models derived from
`vimseo.core.base_integrated_model.PreRunPostModel`{.interpreted-text role="class"} are linking
components deriving from a generic class `vimseo.core.components.base_component.BaseComponent`{.interpreted-text role="class"}.
Three kinds of components are already specialised to play
the role of model pre-processor, run and post-processor, respectively
classes `vimseo.core.components.pre.PreProcessor`{.interpreted-text role="class"},
`~.ModelRun`{.interpreted-text role="class"} and
`~.PostProcessor`{.interpreted-text role="class"}.

## Preprocessors of a model

The preprocessor of a model is the component which is executed first and
prepares data (like meshes) and configuration files for the solver
component. A model can have several preprocessors depending on the
considered load case.

## Solver of a model

The solver of a model is basically the component that puts the problem
defined by the preprocessor into an equation and solves it.

## Postprocessors of a model

The post-processor is a component in charge of applying some treatments
to raw results of the solver and return the outputs to be stored at the
level of the model. A model can have several preprocessors depending on
the considered load case.
