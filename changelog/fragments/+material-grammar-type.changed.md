<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

A `BaseComponent` given a `material_grammar_file` raises a `TypeError` explaining that a material grammar requires a `JSONGrammar` when its input grammar is of another type, instead of an `AttributeError` about `update_from_file`. A model whose first component has no `JSONGrammar` logs a warning that its input bounds are infinite, instead of silently building an unbounded input space.
