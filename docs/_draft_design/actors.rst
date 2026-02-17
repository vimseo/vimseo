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


.. _design_actors:

Actors
======

.. uml::

    "Material modelling expert" as MaterialExpert
    MaterialExpert --> (Review model integration)
    MaterialExpert --> (add knowledge to the model database)
    MaterialExpert --> (develop models)
    MaterialExpert --> (specify sizing process)

.. uml::

    "Decision maker" as DM
    DM --> (Provide requirements)
    DM --> (Provide approved test data)

.. uml::

    "Analysis methodology integrator" as MethodoIntegrator
    MethodoIntegrator --> (Run analysis: calibration, validation, allowables)
    MethodoIntegrator --> (Explore design space: apply transformations on input variables)
    MethodoIntegrator --> (Determine quality of a test data for a given model, determine where more sampling is required.)
    MethodoIntegrator --> (Specify bounds of input design domain for a given application)

.. uml::

    "Model Analysis Expert" as AnalysisExpert
    AnalysisExpert --> (Define analysis process, choose methods)

.. uml::

    "VIMSEO developer" as Dev
    Dev --> (Add or modify generic model features ana analysis capabilities, possibly through plug-ins)

.. uml::

    "Material model user" as User
    User --> (Run a model, use output design values, run optimisations)

.. uml::

    "Material modelling integrator" as ModelIntegrator
    ModelIntegrator --> (Add new model, add reference data)
