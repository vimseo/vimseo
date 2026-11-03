<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

`Curve.compute(x, interpolate=False)` computes the ordinates of a curve at abscissas: the ordinates of the closest points by default, or interpolated linearly with `interpolate=True`, which raises a `ValueError` outside the abscissas of the curve.
