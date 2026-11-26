<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

Each GitHub release publishes a `constraints.txt` holding the dependency versions the
tests of the release pass with, for every OS and every supported Python:
`pip install "vimseo==X.Y.Z" -c <release URL>/constraints.txt` gives a reproducible
environment. `tools/offline_bundle/build_offline_bundle.py` builds a bundle installing
VIMSEO, its plugins and their dependencies on a machine without internet access (see
the Offline installation section of the README).
