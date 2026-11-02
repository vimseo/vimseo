<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

A `BaseDisciplineModel` takes a material, declared by `MATERIAL_FILE` or passed to its
constructor (`material=...`, also through `create_model`). The material values are
the default values of the discipline inputs of the same names. A `ValueError` is
raised when a material property is not an input of the discipline.
