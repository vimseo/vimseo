<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->




### Solution verification for OpfmPlate model PST

The Opfm-based models are verified for the following inputs:

```
PLY_THICKNESS = 0.2
LAYUP = array([-45, 90, 45, 0, 0, 45, 90, -45])
SPECIFIC_INPUTS = {
    "def1c": array([0.005]),
    "def1t": array([0.005]),
    "E1t": array([1.333 * 150000]),
    "E1c": array([0.667 * 150000]),
    "fcv_d_c": array([2.0]),
    "fcv_d_t": array([2.0]),
    "beta22": array([0.2]),
    "element_size": array([2 * PLY_THICKNESS]),
}
```

The main indicators of grid convergence for OpfmPlate PST are summarized below.

{{ read_csv('opfm_plate_pst_indicators.csv') }}

First, if Richardson extrapolation can be computed:

  - its value is given with a $95 \%$ error band.
  - The convergence order is given, together with a $95 \%$ error band.
  - The Grid Convergence Index is given, together with a $95 \%$ error band,
    both for the two finest meshes ($GCI$ requires only two meshes to be computed),
    and the two coarsest. Indeed, if the user wants to make on decision on the use
    of the coarser mesh (which leads to the lowest computational time),
    having indicators on the coarsest meshes is interesting.
  - The RDE on the two coarsest meshes, the two medium meshes and the two finest meshes,
    and the error band on the RDE, computed in the less favourable case
    the two coarsest meshes).

If Richardson extrapolation is not available, the user still has the following indicators:

  - The $GCI$ for an assumed convergence order of two, and the $GCI$ for an assumed
    convergence order of one, both given for the two finest and coarsest meshes.

Here, the RDE is very small, the Grid Convergence Index is close to zero,
and the $95 \%$ confidence interval on Richardson extrapolation is around 1 Mpa, which is very small
compared to the absolute value of 762 MPa.

Then, more details on the Richardson extrapolation can be found in the following figure.

![](cv_opfm_plate_pst.png)

The extrapolation can be computed from three meshes. The four computed meshes are aranged in folds of three meshes,
and for each fold an extrapolation is computed.
For a given fold, the extrapolated value corresponds to the intersection of the curve with the $x = 0$ axis.
The median value for the four extrapolated values and the $95 \%$ convergence interval are reported along the
$x = 0$ axis in orange.

Finally, the following figure shows that the convergence order is roughly two.

![](error_opfm_plate_pst.png)

Raw model input and output data are also available:

{{ read_csv('raw_opfm_plate_pst.csv') }}

These figures and other information about the model can be explored interactively in a dashboard.
The dashboard can be opened by typing ``dashboard_verification`` in a console where VIMSEO environment is activated.
The second tab allows to explore code verification and the third tab is for solution verification exploration.
