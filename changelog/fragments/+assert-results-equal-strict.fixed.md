<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

`assert_results_equal` no longer accepts two different values of the same type: strings, integers, booleans and tuples are now compared by value, whereas only their types were compared. Only the objects that cannot be compared, or that are compared by identity, are still checked by type.
