<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->



# Sensitivity Analysis

## Methodology

Two parameter spaces are generated to assess the influence of the parameter space
on the sensitivity analysis:

- The first one (named $cov=5 \%$) defines triangular distribution
  with the mode being the model default input values,
  and the minimum and maximum computed by a coefficient of variation of $5\%$ around the mode.
  The choice of this coefficient of variation is based on material expert knowledge and
  is expected to be a representative of the material variability.
  If the model default value is zero, then the mode becomes zero and the minimum and maximum
  are respectively $-0.05$ and $0.05$, unless this variable has a bound within this interval.
  In this case, the minimum or maximum is set to the bound value.

- The second one (named $cov=20 \%$) is defined using the same procedure, but with uniform distribution
  and a coefficient of variation of $20 \%$.

Using these two parameter spaces will allow to determine how the sensitivities change for different assumptions
on the variability of the uncertain inputs. We are in particular interested in the robustness of the ranking
of the sensitive inputs.

Three layups are considered. They are expected to reveal different influent parameters on the model outputs:

  - $[30, 90, -30, 90, -30, -30, 90, -30, 90, 30]$
  - $[-60, 0, 60, 0, -60, 60, 60, -60, 0, 60, 0, -60]$
  - $[45, -45, 0, 45, -45, -45, 45, 0, -45, 45]$

Morris sensitivity analysis is performed.
Its cost is larger than a One-at-a-time analysis, but much lower than a Sobol analysis.
It provides richer information than a One-at-a-time analysis for a reasonable computational cost increase.
Morris method can be defined either from:

  - a number of replicates. Default value is 5. Each replicate involves $N+1$ model evaluation,
    where $N$ is the dimension of the input space.
  - a number of samples

Morris has two drawbacks:

  - Both indicator $\mu^*$ and $\sigma$ must be analyzed, since looking only at $\mu^*$
    may lead to underpredict the sensitivity
  - A lack of robustness to a model failure: if a model evaluation fails, the whole analysis is broken

!!! note

    As for other sensitivity analysis based on finite differences,
    Morris sensitivity requires to define a step value to compute the
    finite differences. This step is defined as a ratio, which is multiplied
    by the range of the input variable to obtain the distance between the two
    points used to compute the finite difference.
    The default value for this ratio is $0.05$.
    If we define distributions of the input variable with a coefficient of variation
    of $0.05$, then the step used to compute the finite difference
    relative to input $x_1$ is $Mean(x_1) \times 0.05 \times 0.05$.
    As a result, this step parameter is expected to have a direct impact on the
    sensitivity results. It would be interesting to run the sensitivity analysis for two
    values of this parameter.

## Matrix
