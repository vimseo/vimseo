<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

`SpaceAnalysisNode.update()` can be called directly, as in the examples of `SpaceAnalysisNode`, instead of raising `KeyError: 'statistics'`: its argument `statistics` is now explicit and defaults to `None`. The examples of `SpaceAnalysisNode` are fixed: the center expression uses the parameters `mini` and `maxi`, and the model-based examples use an existing input of `BendingTestAnalytical`.
