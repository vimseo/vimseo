<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->



### Solution verification of OpfmPlate model OHT

![](cv_opfm_plate_oht.png)

The above figure shows that the solution oscillates with respect to the number of degrees of freedom of the mesh,
which is far from the ideal behaviour of asymptotic convergence.
It is thus not possible to obtain the classical indicators for mesh convergence,
like Richardson extrapolation (which would be the converged solution,
i.e. the one obtained for an element size of zero),
or the convergence order.

However, we can still compute the largest difference between the four solutions
relatively to the median value, which is around $1 \%$.
It is similar to the Grid Convergence Index, which can be computed with the assumption of a convergence order.
Here, for a convergence order one and two, the $GCI$ does not exceed $2 \%$ either
for the two finest or two coarsest meshes.
It indicates that the solution is reasonably converged, though the numerical error is not negligible.

{{ read_csv('opfm_plate_oht_indicators.csv') }}

It would be interesting to systematize this kind of analysis for any new layup under analysis.
In addition, it would be interesting to explore higher mesh coarsening to estimate if
simulations with this model can be reliably run for coarser mesh than the default one
(which is currently the one for ``coarsening_factor=1``.)
A database would be very useful to store these verification results.
