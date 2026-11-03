<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

The factories of models, load cases and components explain why a class is not available: how it must be declared and named, e.g. `{Family}_{LoadCase}` for a component, the available classes of the same family, and the modules that could not be imported, whose classes are hidden. A component or a model whose constructor does not accept its arguments raises a `TypeError` naming the class and the arguments; `ComponentFactory.create` no longer returns `None` in that case.
