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


.. _design_calibration:

Calibration architecture
------------------------

.. uml:: seq_calibration.puml


.. Activity diagram
.. ================
..
.. For the "Set up model analysis pipeline" use case.
..
.. .. uml::
..
..   (*) --> "Specify application domain"
..   -->[Output: parameter space. Which shape is supported?] "Specify calibration sequence"
..   -->[Output: lists of test points.\n Each list considers the variation of a single parameter] "Perform sensitivity analysis"
..   -->[Output: Output: list of most influential parameters,\n coverage of parameters by calibration sequence,\n Update calibration matrix] "Perform calibration"
..   -->[Output: coverage of calibration matrix with available data,\n Update hypothesis on parameters (restrict parameter space)]  "Perform validation"
..   -->[Output: coverage of application domain with available data,\n Error map] (*)
..
..
.. Component diagram
.. =================
..
.. .. uml::
..
..   package "VIMSEO core" {
..     [Material model integration]
..     [Analysis pipeline integration]
..     [Application requirement integration]
..   }
..
..   database "HDF5" {
..     folder "Analysis pipelines" {
..       [Analysis pipeline]
..     }
..     folder "Tests" {
..       [Test]
..     }
..     folder "Material properties" {
..       [Material property]
..     }
..     folder "Application requirements" {
..       [Application requirement]
..     }
..   }
..
..   [Material model integration] --> [Material property]
..   [Material model integration] --> [Test]
..   [Analysis pipeline integration] --> [Analysis pipeline]
..   [Application requirement integration] --> [Application requirement]
