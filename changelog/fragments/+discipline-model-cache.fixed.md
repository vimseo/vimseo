<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

The cache of the discipline wrapped by a `BaseDisciplineModel` (GEMSEO sets a
`SimpleCache` by default) is now disabled, the model managing the cache. With the
model cache disabled, it still answered: the discipline was not executed but the
model archived a new simulation.
