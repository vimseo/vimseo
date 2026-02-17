<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->




General

- QoI: Quantity of Interest
- MDO:
    Multi-Disciplinary Optimization.

- Coupon tests:
    Tests mechanical properties of a material on standard shapes and TODO sollicitation

Verification:

- GCI: Grid Convergence Index
- RDE: Relative Discretization Error

Composites:

- PS: Plain Strength
- OH: Open Hole

Load cases:

- LC: Load Case
- PST: Plain Strength Tension
- PSC: Plain Strength Compression
- OHT: Open Hole Tension
- OHC: Open Hole Compression

Material:

- material grade:
    Can be titanium or steel for example

Uncertainty Quantification

-  b-value
    Material tests are subjected to uncertainties
    due to variability in material properties
    or test bench.
    In general, several tests are repeated on a batch of material.
    B-value is an estimator of a ten percent quantile of a material property.
    It takes into account the fact that the number of tests
    may not be sufficient to obtain converged statistics.
    The tests may measure deformation against applied force.
    Based on several curves, the maximum force value above which plastic deformation occurs
    can be estimated.
    Different values of this maximum force are obtained on a batch.
    B-value allows to estimated a conservative maximum force value
    taking into account variability in testing and material properties.
