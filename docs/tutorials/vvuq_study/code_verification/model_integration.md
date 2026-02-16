<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

<!--
 Copyright (c) 2015 IRT-AESE.
 All rights reserved.

 Contributors:
    INITIAL AUTHORS - API and implementation and/or documentation
        :author: XXXXXXXXXXX
    OTHER AUTHORS   - MACROSCOPIC CHANGES
-->

## A component-based model integration for model verification

As we expect to integrate a large number of models,
it is interesting to define a strategy for model integration that will ease
the verification and maintainability of these models.
We rely on the concept of Travelling Model. A Travelling Model means:

- Same physics (e.g. damage law)
- Same geometrical idealisation
- Same numerical approximations (e.g. meshing rules)

As a result, it makes sense to define components corresponding to each above bullets,
and build the models by assembling these components.
Then, verifying a component (through a given model) will ensure the verification
of this component for all the model using it.
In terms of maintainability, it is also more efficient to share components across
models to reduce the code base.

![](component_based_approach.png){ width="500" }

Regarding model implementation, the models are composed of three components:
a pre-processor, a run-processor and a post-processor.
Pre-processor and post-processor embed the meshing strategy, while the run-processor uses the
damage law and implements a given modelling strategy, as explained below.


## Modelling strategies

Defining different modelling approach having different fidelity level
eases model calibration and validation,
because the best compromise in terms of fidelity versus computational time can be chosen.
Indeed these two activities involve a large number of model runs:
- calibration is based on several gradient-free optimizations with a design space composed
  of around five to ten variables
- stochastic validation involves a Monte-Carlo uncertainty propagation at each validation point

![](modelling_strategies.png){ width="600" }

The three following modelling approaches have been developped:

  - The OpfmUnitCell model. It does not require a finite-element solver and it
    does not account for the geometry or the stacking sequence.
    This model runs the material law within a convergence loop that is developed in
    a specific ``run-processor`` (see TODO insert link to vims doc).
    It considers a pure loading mode only.
    Its computational time is less than one min on a single CPU, except for the PureShear load case.
    It is useful for calibration, sensitivity analysis and
    load cases with uniform stress distribution (pure tension/ compression/shear).

    ![](opfm_unitcell_workflow.PNG){width="200"}

  - The OpfmCube model.
    It is based on the RVE (Representative Volume Element) approach.
    It only accounts for the thickness of the specimen,
    and considers a uniform stress distribution per ply.
    So it does account for the stacking sequence.
    It requires Abaqus as a finite-element solver and
    uses the single 3D solid element approach with multiple integration points
    through the thickness.
    Its computational time is a few minutes on a single CPU.
    It is useful for calibration, sensitivity analysis and
    load cases with uniform stress distribution (some PS)

  - The OpfmPlate model.
    It accounts for the actual geometry of the specimen
    and for the stacking sequence.
    The PS geometries are modelled with ply-by-ply with 3D solid elements,
    while the OH is modelled with laminated shell.
    The computational time is at least one order of magnitude larger
    than the OpfmCube model.

    ![](opfm_plate_pst_mesh.PNG){width="500"}
