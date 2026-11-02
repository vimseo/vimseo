<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

A model wrapping a GEMSEO discipline can be declared in a YAML file, without writing
Python nor installing code. The models declared in the directories of
`VIMSEO_MODELS_PATH` are created by name, as any model. The command `vimseo_wrap`
writes the JSON input grammar of a declared model from its discipline
(`write-grammar`), to be completed with bounds, and checks a declaration (`check`),
telling whether `create_model` finds the model. See the example
`02_integrated_models/plot_06_declarative_model.py`.
