<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->



# Abstract for ASME 2025

To face the challenge of developing disruptive designs and reduce time-to-market,
one key enabler is to make part of the development process virtual.
This process necessarily includes iterations where the current design is tested,
like the test pyramid approach in the domain of the design of structure ([@doeland2020], [@freitas2020standards]).
Obtaining an efficient hybrid testing process relies on optimizing the complementarity
between the physical and virtual tests.
Indeed, they both represent the real system with different sources of errors and uncertainties.
The physical tests may serve to verify, validate or participate to data-driven models, and virtual tests may serve to
provide complementary measures on the real system (inaccessible to physical sensors)
as well as optimizing the test matrix and test setups.
As a result, virtual testing processes shall not only include numerical models, but also mathematical methods
from, not exhaustively, the fields of uncertainty quantification and optimization.

It is proposed that to foster an efficient transfer of such academic methods and modelling
towards industry,
a virtual testing platform shall meet the following high level requirements:
  - fit to several types of users, including web user engineer, advanced script user engineer,
    mathematical method experts, numerical model experts,
    physics experts, decision-makers, model and method integrators.
  - be user-friendly to non-software specialists to allow efficient integration
    of new mathematical methods and numerical models,
  - allow a reliable assessment of the credibility of the virtual process,
  - ensure flexibility and scalability on usage of computational ressources to target a given lead time

For a successful integration in a given organization,
the virtual testing platform must also comply to organization-specific requirements and application field specificities,
including expected lead time, availability of modelling tools and methods, computational ressources
and available test data.
Indeed, the choice of a mathematical method for uncertainty quantificaiton, the model features
(input and output space dimensionality, non-linearity, computational cost) and the available test data are intricated.
For instance, validating models with very sparse reference data with very few repeats,
or using a heavy numerical model for which each simulation runs during several hours requires specific
UQ methods.

It is argued that an efficient way of making sure that the platform implements all the necessary analysis bricks and models
regarding the industrial specification
(in terms of input output interface, UQ method and computational load management)
is to allow a fast prototyping of typical end-to-end workflows.

The VIMSEO platform under development at IRT Saint Exupery implements such a workflow approach based on the
workflow engine of GEMSEO. VIMSEO integrates VV&UQ scenarios such as solution verification, code verification
stochastic validation, efficient design value estimation, together with more generic bricks
(sensitivity analysis, design of experiment, surrogate modelling).
Since compatible with GEMSEO [@gallard2018gemseo], it can seamlessly integrate advanced optimization algortihms
and multi-disciplinary optimization bricks in the workflows.

To assess the capability of VIMSEO to generate and execute realistic VV&UQ workflows,
one of its plugins is dedicated to composite damage modelling, and integrates several state-of-the-art parametric
models of composite coupons and basic structure components.
End-to-end VV&UQ workflows involving these composite damage models are presented, from the workflow-prototyping interface
to the dashboards for result exploration.

Still, several features are in-progress, like database storage for traceability,
the definition of global taxonomy to ease interoperability
between models, data and UQ methods,
and the development of efficient intrusive and non-intrusive stochastic analysis for heavy models.

[//]: # (Indeed, it allows to define with the mathematical method experts, engineers and decision makers )
[//]: # (the inputs, outputs and options)
[//]: # (of each workflow brick, identify generic ones, choose the computational ressources with numerical model experts and)
[//]: # (the necessary visualizations for decision-making.)
