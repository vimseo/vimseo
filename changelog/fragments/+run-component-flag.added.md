<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

`BaseComponent.is_run_component` tells whether a component runs the external software of its model: `PreRunPostModel` sets it on its run-processor, and `IntegratedModel.run` is the component having it, else the first component, instead of the component at a position given by the private `_RUN_COMPONENT_INDEX`, which is removed. `IntegratedModel.run` raises a `ValueError` when several components have it.
