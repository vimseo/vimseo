<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

**Breaking change:** the bounds of the material of a model shall be within the
bounds of the JSON input grammars of its components, so that an uncertain space
built from the material only yields valid inputs. Otherwise, the construction of
the model raises a `ValueError` naming the properties concerned. A material
property without bounds (±1e12 by default) is thus rejected when the grammar
bounds the input.
