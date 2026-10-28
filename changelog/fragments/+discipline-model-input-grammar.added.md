<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

A `BaseDisciplineModel` bounds its inputs with a JSON grammar file, declared by
`_INPUT_GRAMMAR_FILE`, which can only restrict the input grammar of the discipline.
The component wrapping the discipline gets a JSON grammar built from the discipline
one and restricted by the file, from which the model input bounds are read; the
input grammar of the model remains a `SimplerGrammar`, and the discipline keeps its
own grammar. An input out of the bounds makes the simulation fail.
