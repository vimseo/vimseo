<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->



# Abstract for ECCOMAS 2024

Key Words: Composite structures, VV&UQ platform, Parametric Finite-Element model

The Aerospace Industry is facing the challenge of developing and integrating disruptive
technological innovations by 2035-2050. It means that disruptive design or designs with limited
in-service experience need to be integrated in shorter times with high levels of safety and
reliability. Composite structures play a major role in this transition, but have to adapt to new
designs, new threats (cryogenic temperatures), new material (bio-sourced) and new
manufacturing and assembly processes.
A key enabler for the reduction of development cycle time and cost is the integration of more
simulations in the certification test pyramid. As a result, the simulation of composite structures
must reach a high level of credibility.

VV&UQ builds and assesses credibility of models through methodologies ([1], [2]) which bring
to play several components like Numerical Simulation tools and Mathematical algorithms, High
Performance Computing submission and monitoring, and so forth. The notions of traceability
(of both functional capabilities (like models) and data), data visualisation and standardized
taxonomy to describe the manipulated quantities and methods are also significantly contributing
to the credibility and the decision-making process. Note that some components may already
exist and can be re-used off-the-shelf (UQ methodologies, FE software).

The present work focuses on an efficient software implementation of the VV&UQ process to
support the above challenges. VIMSEO (Virtual testing Integration platform for decision-Making
Support) is a Python library (still under construction) developed from the translation of
VV&UQ processes into software requirements. Some of them are listed hereafter:

- The integration of state-of-the-art simulation models and methodologies for Uncertainty
  Quantification requires interfacing experts in these domains.
- Decision-makers must also interface to the platform to validate the process establishing
  credibility. Thus, relevant data visualisation and an effective User Interface is necessary.
- Traceability of models and associated analysis methods is also necessary both for
  credibility assessment and further use of the models and methodologies for
  optimisation, calculation of design values and structural sizing. The platform should
  then be closely linked with databases.
- Model standardization through a global taxonomy or ontology and a semantic layer is
  also a key feature since it allows to seamlessly change models and analysis
  methodologies, and also use the verified models in other frameworks like MultiDisciplinary Optimisation (MDO) processes, without re-implementing the model.

While generic, the VIMSEO platform is extended for applications to composite structures [3] in a
plug-in integrating Composite Damage Models (OPFM [@laurin2007opfm] and PG [@maimi2007pg]) at coupons and element
levels. Several parametric FE models are integrated under a consistent model template,
compatible with the MDO platform GEMSEO [@gallard2018gemseo]. Each FE model integrated in the platform is
decomposed in bricks allowing to inter-change different load cases and material definition
while making sure that we keep the same numerical model (FE method and material law). The
latter constitutes the Travelling Model [@romero2011_model_validation]. We will focus on the model Verification and
Validation bricks, including an example of stochastic validation.

References:

  - [1] ASME V&V 10.3 Validation Metrics
  - [2] ASME V&V 10-2019 Standard Verification and Validation in Computational Solid
  Mechanics
  - [3] J. Fatemi, G. Poort, Towards Qualification of Composite Launcher Structures by
  Simulation, 17th ECCSMET Proceedings, 28-30 March 20203, Toulouse.

[@riedmaier2020unifiedvvuq]
