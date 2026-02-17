..
    Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

    This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
    International License. To view a copy of this license, visit
    http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
    Commons, PO Box 1866, Mountain View, CA 94042, USA.

..
    Copyright (c) 2019 IRT-AESE.
    All rights reserved.

    Contributors:
       INITIAL AUTHORS - API and implementation and/or documentation
           :author: Sebastien BOCQUET
       OTHER AUTHORS   - MACROSCOPIC CHANGES

..
   Copyright (c) 2020 IRT-AESE
   All rights reserved.

   Contributors:
          :author: Sebastien Bocquet


.. _design_intro:

Overview
========

An objective is to link closely the implementation of the mechanical model
with its definition and the modeling hypothesis.
These hypothesis and definitions may be:

  - geometrical
  - numerical
  - applicablity domain
  - physical (material)

The notion of load case was introduced in |v|
to represent a set of geometrical configurations,
each corresponding to a type boundary condition
for the mechanical model.
It may be seen as a categorical variable among
the other (continuous) variables that parametrize the model.
It is also useful to link the model to a given test
(typically coupon tests).

The following concepts may be useful to intoduce into |v|:

  - ``Material``
  - ``BoundaryCondition``
  - ``Field``, with a ``Scalar``, ``1D``, ``2D`` declination
  - ``Mesh``

The objective is not that |v| proposes some post-processing on these ``Fields``
(on the sense of slicing, cutting, averaging etc...).
Rather, |v| should be able to read ``Fields`` (obtained from user scripts)
and provide some storage and plotting capabilities.
These capabilities should take into account temporal data.

Lower priority needs may be to:

  - convert some model for another mechanical solver (Abaqus to Nastran for instance)
  - transfer the Jacobian matrix from the mechanical solver
    to an MDO scenario or sensitivity analysis.
