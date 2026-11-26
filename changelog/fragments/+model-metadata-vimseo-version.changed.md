<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

The `vims_git_version` metadata of a model stores the version of VIMSEO when it is a tagged release, and the git commit otherwise. When the commit cannot be determined (no git repository, no git), it stores the installed version instead of an empty string, and an information message is logged once per process instead of a warning at each execution.
