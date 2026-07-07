<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->



## Results for OpfmPlate OHT

Layup $[45, 0, 135, 90, 90, 135, 0, 45]$

| $cov=5 \%$                 |
|----------------------------|
| ![](oht/bar_plot_5pct.png) |

| $cov=20 \%$                 |
|-----------------------------|
| ![](oht/bar_plot_20pct.png) |

Based on the max force, the most sensitive inputs are
$E_1$, $X_t$, $E_{1t}$ and $def_{1t}$.

| $cov=5 \%$                              | $cov=20 \%$                              |
|-----------------------------------------|------------------------------------------|
| ![](oht/morris_plot_max_force_5pct.png) | ![](oht/morris_plot_max_force_20pct.png) |
| ![](oht/morris_plot_modulus_5pct.png)   | ![](oht/morris_plot_modulus_20pct.png)   |

Interestingly, based on the max force, the sensitivity ranking of the inputs
is different on the two parameter spaces.

## OpfmPlate OHC model
