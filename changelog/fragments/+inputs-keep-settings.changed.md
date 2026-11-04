<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

`BaseAnalysisNode.execute(inputs=...)`, without `settings`, keeps the settings set before, e.g. with `update_options` or `options[...]`, instead of resetting them to their default values; only the missing settings take their default values. Any other argument passed with `inputs`, e.g. a misspelled `settings`, raises a `ValueError` instead of being ignored, and inputs of a wrong type raise a `TypeError`.
