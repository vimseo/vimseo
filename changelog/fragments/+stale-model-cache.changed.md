<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

A model whose HDF5 cache holds outputs that do not match its output grammar, e.g. a cache written by an older version of the model or of VIMSEO, now backs up the cache file as `<name>.stale-<UTC date>.hdf`, clears the cache and executes, instead of failing with a `KeyError` or an `InvalidDataError`.
