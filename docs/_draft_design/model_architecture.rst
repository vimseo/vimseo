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


.. _design_model:

Model architecture
==================

Class diagram
-------------

Current developments are moving towards the architecture shown below (red elements are meant to disappear and cyan elements are about to be implemented):

.. uml:: vims_architecture_objective.puml


Examples of integration
-----------------------

Case of integrating a new analytical model:

.. uml:: model_integration_analytical.puml

Case of integrating a new Abaqus model:

.. uml:: model_integration_abaqus.puml
