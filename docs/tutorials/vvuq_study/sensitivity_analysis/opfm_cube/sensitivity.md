<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->



## Results for OpfmCube

The results for the OpfmCube model are presented based on the sensitivity viewer dashboard,
which can be obtained by typing ``dashboard_sensitivity`` in a console where VIMSEO is installed:

## OpfmCube PST

### Layup $[30, 90, -30, 90, -30, -30, 90, -30, 90, 30]$

We present the plots available in the ``dashboard_sensitivity``.
These plots are specialized for a Morris analysis.
Other type of sensitivity analysis would be visualized through
specific plots.
First, a bar plot summarizes the sensitivity of one or several outputs
to all inputs. A ``standardize`` option can be used to scale
the highest sensitivity to one. For a Morris analysis,
the $\mu^*$ indicator is shown.

| $cov=5 \%$                                    |
|-----------------------------------------------|
| ![](layup_30_90_PST/space_5_pct/bar_plot.png) |

A radar plot representation for $\mu^*$ index is also available.
Based on the max strength, the most sensitive variables are
$X_t$, $E_{1t}$ and $E_1$.

Finally, more details about the sensitivities can be obtained
with the $\sigma$ versus $\mu^*$ plots.
A single output is selected on each plot.
The value of $\sigma$ represents how much the relationship of the output
versus an input is non-linear.

| $cov=5 \%$                                                    |
|---------------------------------------------------------------|
| ![](layup_30_90_PST/space_5_pct/morris_plot_max_strength.png) |
| ![](layup_30_90_PST/space_5_pct/morris_plot_modulus.png)      |


### Layup $[-60, 0, 60, 0, -60, 60, 60, -60, 0, 60, 0, -60]$

| $cov=5 \%$                                    |
|-----------------------------------------------|
| ![](layup_-60_0_PST/space_5_pct/bar_plot.png) |

Based on the max strength, the most sensitive variables is
$X_t$.

Finally, more details about the sensitivities can be obtained
with the $\sigma$ versus $\mu^*$ plots.

| $cov=5 \%$                                                    |
|---------------------------------------------------------------|
| ![](layup_-60_0_PST/space_5_pct/morris_plot_max_strength.png) |
| ![](layup_-60_0_PST/space_5_pct/morris_plot_modulus.png)      |


### Layup $[45, -45, 0, 45, -45, -45, 45, 0, -45, 45]$

| $cov=5 \%$                                     |
|------------------------------------------------|
| ![](layup_45_-45_PST/space_5_pct/bar_plot.png) |

Based on the max strength, the most sensitive variables is
$X_t$ and $S_{12}$.

Finally, more details about the sensitivities can be obtained
with the $\sigma$ versus $\mu^*$ plots.

| $cov=5 \%$                                                     |
|----------------------------------------------------------------|
| ![](layup_45_-45_PST/space_5_pct/morris_plot_max_strength.png) |
| ![](layup_45_-45_PST/space_5_pct/morris_plot_modulus.png)      |


## OpfmCube PSC

### Layup $[30, 90, -30, 90, -30, -30, 90, -30, 90, 30]$

| $cov=5 \%$                        |
|-----------------------------------|
| ![](layup_30_90_PSC/bar_plot.png) |

| $cov = 5 \%$                        |
|-------------------------------------|
| ![](layup_30_90_PSC/radar_plot.png) |

Based on the max strength, the most sensitive variables are
$X_c$, $S_{12}$, $E_1$, $G_{12}$ and $E_{1c}$.

Finally, more details about the sensitivities can be obtained
with the $\sigma$ versus $\mu^*$ plots.

| $cov=5 \%$                                                   |
|--------------------------------------------------------------|
| ![](layup_30_90_PSC/morris_plot_max_strength.png) |
| ![](layup_30_90_PSC/morris_plot_modulus.png)      |


### Layup $[-60, 0, 60, 0, -60, 60, 60, -60, 0, 60, 0, -60]$

The same plots are now shown for another layup.

| $cov=5 \%$                                    |
|-----------------------------------------------|
| ![](layup_-60_0_PSC/space_5pct/bar_plot.png)  |

| $cov=20 \%$                                   |
|-----------------------------------------------|
| ![](layup_-60_0_PSC/space_20pct/bar_plot.png) |

We note that the sensitivities are very close for the two
parameter spaces. Thus, for this layup, the sensitivities are mostly independent
of the width of the distribution around the default input values.
Based on the max strength, the most sensitivity variables are $X_c$, $E_1$.

TODO: why the variable names are not shown on some plots?

| $cov=5 \%$                                                   | $cov=20\%$                                                    |
|--------------------------------------------------------------|---------------------------------------------------------------|
| ![](layup_-60_0_PSC/space_5pct/morris_plot_max_strength.png) | ![](layup_-60_0_PSC/space_20pct/morris_plot_max_strength.png) |
| ![](layup_-60_0_PSC/space_5pct/morris_plot_modulus.png)      | ![](layup_-60_0_PSC/space_20pct/morris_plot_modulus.png)      |


### Layup $[45, -45, 0, 45, -45, -45, 45, 0, -45, 45]$

| $cov=5 \%$                                         |
|----------------------------------------------------|
| ![](layup_45_-45_PSC/space_5pct/bar_plot.png) |

| $cov=20 \%$                                        |
|----------------------------------------------------|
| ![](layup_45_-45_PSC/space_20pct/bar_plot.png) |

Again, the $\mu^*$ indicator is mostly independent of the
two chosen parameter spaces.
Based on the max strength, the most sensitivity variables are $X_c$, $G_{12}$ and $E_1$.

| $cov=5 \%$                                                    | $cov=20\%$                                                     |
|---------------------------------------------------------------|----------------------------------------------------------------|
| ![](layup_45_-45_PSC/space_5pct/morris_plot_max_strength.png) | ![](layup_45_-45_PSC/space_20pct/morris_plot_max_strength.png) |
| ![](layup_45_-45_PSC/space_5pct/morris_plot_modulus.png)      | ![](layup_45_-45_PSC/space_20pct/morris_plot_modulus.png)      |

However, the non-linearity magnitude are very different between the two
parameter spaces.
