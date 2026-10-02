<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Calibration: metrics and optimizer settings

This page describes how ``CalibrationStep`` turns the gap between the simulated and the
reference outputs into one objective function, and how to choose the optimizer
settings from what you know about the data: the measurement scatter, the numerical
noise of the model, the precision you need, and the computational budget.

Sections 1 to 3 are generic. Section 4 applies them to an example.

## 1. The calibration objective

Each control output $k$ of each load case is compared to its reference data
with a metric $M_k$.
The optimizer minimizes the weighted sum

$$
J(\theta) = \sum_k w_k \, M_k(\theta)
$$

where $\theta$ is the vector of calibrated parameters.

The weights $w_k$ are those of ``CalibrationMetricSettings.weight``
(from gemseo-calibration):

- each weight is in $[0, 1]$ and the weights sum to 1;
- the metrics whose weight is ``None`` share equally what the others leave.

When the same output is calibrated on several load cases,
each load case contributes its own term.

!!! note

    Since the weights sum to 1, $J$ is a weighted average of the metrics.
    When all the metrics are dimensionless and of similar magnitude
    (see the scaling below), $J$ can be read as a typical squared relative error.
    This is what makes it possible to choose the optimizer tolerances
    from physical considerations (Section 3).

## 2. Metrics

A metric is chosen with ``CalibrationMetricSettings.metric_name``.
Metrics fall into two families:

| Family | Output type | Metrics | Needs ``mesh_name`` |
|---|---|---|---|
| Mean metrics | scalar or vector | ``MSE``, ``MAE``, ``RelativeMSE`` | no |
| Integrated metrics | curve $y(x)$ | ``ISE``, ``IAE``, ``SBPISE`` | yes (the $x$ variable) |

``MSE``, ``MAE``, ``ISE`` and ``IAE`` come from gemseo-calibration.
``RelativeMSE`` and ``SBPISE`` are defined in
``vimseo.tools.calibration.calibration_metrics``.

### 2.1 Mean metrics

Let $y^{ref}_{i}$ and $y_{i}(\theta)$ be the reference and simulated values,
where $i$ runs over the reference samples and the vector components.
NaN values are ignored in the mean.

| Metric | Definition | Unit |
|---|---|---|
| ``MSE`` | $\operatorname{mean}_i \left(y^{ref}_i - y_i\right)^2$ | output unit squared |
| ``MAE`` | $\operatorname{mean}_i \left\lvert y^{ref}_i - y_i\right\rvert$ | output unit |
| ``RelativeMSE`` | $\operatorname{mean}_i \left(\dfrac{y^{ref}_i - y_i}{y^{ref}_i}\right)^2$ | dimensionless |

``RelativeMSE`` is the square of the relative error $e$.
This gives a direct reading of its values:

| Relative error $e$ | 1 % | 2 % | 5 % | 10 % | 20 % |
|---|---|---|---|---|---|
| ``RelativeMSE`` $= e^2$ | 1e-4 | 4e-4 | 2.5e-3 | 1e-2 | 4e-2 |

!!! warning

    ``MSE`` and ``MAE`` carry the unit of the output.
    Combining them with other metrics in the same objective makes the weights
    depend on the units, for instance MPa versus GPa.
    Prefer ``RelativeMSE``, unless a reference value is close to zero:
    ``RelativeMSE`` divides by it.

### 2.2 Integrated metrics: ``ISE`` and ``IAE``

For each reference sample, the simulated curve is linearly interpolated on the
reference abscissas $x^{ref}$. The error is then integrated with the trapezoidal rule:

$$
\mathrm{ISE} = \operatorname{mean}_{samples} \int \left(y^{ref}(x) - y(x)\right)^2 dx,
\qquad
\mathrm{IAE} = \operatorname{mean}_{samples} \int \left\lvert y^{ref}(x) - y(x)\right\rvert dx
$$

Extrapolation is forbidden.
The simulated curve must cover the whole reference abscissa range,
otherwise the evaluation fails.
This is a common problem when a simulation stops before the end of the test,
for instance at a convergence failure or a final rupture.
``SBPISE`` handles this case.

### 2.3 ``SBPISE``: Scaled, Bound-Penalized Integrated Square Error

``SBPISE`` is an ``ISE`` with two additions:

- an optional scaling of both curves, which makes the metric dimensionless;
- a tolerance to curves with different abscissa supports, plus an optional
  penalization of the support mismatch.

For each reference sample, the computation goes through the following steps.

1. **Sort** both curves by increasing $x$.
   If the two abscissa ranges do not overlap, or if one of them is a single point,
   an error is raised.

2. **Scale** (only with ``scaling=CurveScaling.XYRange``).
   Both curves are centered on the mean of the reference data,
   $x_0 = \operatorname{mean}(x^{ref})$ and $y_0 = \operatorname{mean}(y^{ref})$.
   They are then divided by the largest range of the two curves:

    $$
    \tilde{x} = \frac{x - x_0}{L_x}, \quad L_x = \max\left(\operatorname{range}(x^{ref}), \operatorname{range}(x)\right),
    \qquad
    \tilde{y} = \frac{y - y_0}{L_y}, \quad L_y = \max\left(\operatorname{range}(y^{ref}), \operatorname{range}(y)\right).
    $$

    After scaling, both curves fit in a unit box.
    Different outputs, and different load cases, then produce values of the same
    magnitude.
    With ``scaling=CurveScaling.NONE``, the curves are used as they are.

3. **Measure the support mismatch** (in scaled units with ``XYRange``):

    $$
    \delta_L = \lvert \tilde{x}_0 - \tilde{x}^{ref}_0 \rvert,
    \qquad
    \delta_R = \lvert \tilde{x}^{ref}_{end} - \tilde{x}_{end} \rvert.
    $$

4. **Integrate on the overlap.**
   The reference grid is enriched with the simulated abscissas that fall inside
   the reference range, then restricted to the overlap of both supports.
   Both curves are interpolated on this grid, and the squared difference is
   integrated:

    $$
    A = \int_{overlap} \left(\tilde{y}^{ref}(\tilde{x}) - \tilde{y}(\tilde{x})\right)^2 d\tilde{x}.
    $$

5. **Combine.** With the penalization factors $p_L$ = ``x_left_penalization_factor``
   and $p_R$ = ``x_right_penalization_factor``:

    $$
    \mathrm{SBPISE} = \operatorname{mean}_{samples}
    \frac{A + p_L \, \delta_L^2 + p_R \, \delta_R^2}{1 + p_L + p_R}.
    $$

    With $p_L = p_R = 0$ (the default), $\mathrm{SBPISE} = A$.

**How to read the value.**
With ``XYRange``, let $\ell \le 1$ be the scaled length of the overlap,
and let $e = \mathrm{RMS}(y^{ref} - y) / L_y$ be the RMS error relative to the
amplitude of the curves. Then

$$
\mathrm{SBPISE} \approx \ell \, e^2 .
$$

For full overlap, ``SBPISE`` reads like ``RelativeMSE``: an RMS error of 5 % of the
curve amplitude gives about 2.5e-3.
Both metrics can therefore be mixed in the same objective with comparable weights.

!!! warning "Caveats"

    - **A truncated curve is not penalized by default.**
      Without penalization, only the overlap is compared.
      A simulated curve that stops early is judged on its first part only,
      and can obtain a *lower* value than a complete curve.
      When the extent of the curve matters, for instance the displacement at
      rupture, set $p_L$ or $p_R$ to a positive value.
    - **The scale depends on the simulated curve.**
      $L_x$ and $L_y$ take the maximum over both curves.
      A simulated curve with an exaggerated amplitude therefore increases $L_y$,
      which slightly reduces its own error.
      This effect is small when the simulated and reference amplitudes are close.
    - **Points outside the overlap are ignored**, both on the simulated and on the
      reference side.
    - ``XYRange`` is required whenever a step combines several metrics or several
      load cases. Otherwise, the terms of $J$ have different units and magnitudes.

### 2.4 Choosing a metric

| Situation | Recommended metric |
|---|---|
| Scalar or vector outputs, values far from zero | ``RelativeMSE`` |
| Scalar outputs close to zero | ``MSE``, with an explicit normalization of the output |
| Curves covering the full reference range | ``SBPISE`` with ``XYRange``, or ``ISE`` |
| Curves that may stop before the end of the test | ``SBPISE`` with ``XYRange``, and $p_R > 0$ if the extent matters |
| Several outputs or load cases in one step | normalized metrics only: ``RelativeMSE``, ``SBPISE`` with ``XYRange`` |

## 3. Choosing the optimizer settings

The default optimizer is ``NLOPT_COBYLA``.
It is gradient-free and builds successive linear approximations of $J$ inside a
trust region that shrinks as it converges.
Most of what follows also holds for the other gradient-free algorithms,
such as ``NLOPT_BOBYQA`` or ``NELDER-MEAD``.

### 3.1 How the stopping criteria work

The stopping criteria are evaluated by GEMSEO, not by NLopt.
GEMSEO disables NLopt's own ``ftol``/``xtol`` and checks its own criteria at every
iteration:

- **Objective tolerance.**
  Let $J_1, \dots, J_{n_x}$ be the last $n_x$ values of $J$, and $\bar{J}$ their mean.
  The run stops when every value satisfies
  $\lvert J_j - \bar{J}\rvert \le$ ``ftol_abs`` $+$ ``ftol_rel`` $\cdot \lvert\bar{J}\rvert$.
  The message is *"Successive iterates of the objective function are closer than
  ftol_rel or ftol_abs"*.
- **Design tolerance.**
  The same test is applied to each parameter, with ``xtol_abs`` and ``xtol_rel``.
  It uses the physical (non-normalized) values of the parameters.
- **Window size.** $n_x$ is ``stop_crit_n_x``.
  When it is left to ``None``, it is $n+1$ for ``NLOPT_COBYLA`` and $2n+1$ for
  ``NLOPT_BOBYQA``, where $n$ is the number of parameters. Otherwise it is 3.
- **Other limits.** ``max_iter`` is the maximum number of iterations;
  NLopt additionally stops at $1.5 \times$ ``max_iter`` evaluations.
  ``max_time`` is a wall-clock limit.
  ``stopval`` stops the run as soon as $J \le$ ``stopval``.

!!! warning "Zero tolerances do not disable the criteria"

    The objective and design tests run whatever the tolerance values are.
    With ``ftol_abs = ftol_rel = 0``, the objective test still triggers as soon as
    the last $n_x$ values of $J$ are *exactly* equal.
    This happens when the objective is piecewise constant in a parameter,
    which is typical of discrete parameters such as a mesh size.
    A mesh size is turned into an integer number of elements, so neighbouring values
    give the same mesh, hence bit-identical outputs.
    With one parameter and $n_x = 2$, two neighbouring evaluations are enough to stop
    the run.
    The only setting that controls this is ``stop_crit_n_x``.
    Better still, do not calibrate discretization parameters at all:
    fix them by a mesh-convergence study
    (see [Solution verification](solution_verification/solution_verification_method.md)).

### 3.2 What you need to know first

Each setting below derives from one of these quantities.
You do not need all of them: each rule states what it requires,
and a default is given when the quantity is unknown.

| Symbol | Quantity | How to obtain it |
|---|---|---|
| $\sigma_{exp,k}$ | Relative measurement scatter on output $k$ | Repeated tests (coefficient of variation), or measurement-chain uncertainty |
| $\sigma_{num}$ | Numerical noise on $J$ | Estimated with the protocol of Section 3.4 |
| $e^*$ | Relative error expected at the optimum | See below |
| $\Delta e$ | Smallest change of relative error worth paying for | Your engineering judgement, e.g. 0.1 point |
| $S_j$ | Sensitivity of the outputs to parameter $j$ | Physics, or the evaluations of Section 3.4 |
| $t_{eval}$ | Cost of one model evaluation | A single run |

**The expected error at the optimum, $e^*$.**
With normalized metrics, $J \approx e^2$, where $e$ is the relative error between the
simulated and the reference outputs, averaged over the outputs with the weights $w_k$.
$e^* = \sqrt{J^*}$ is the value of $e$ that you expect when the calibration has
converged.

It is needed because the optimizer works on $J$, not on $e$, and the conversion
depends on where you are: a change $\Delta e$ of the error changes $J$ by
$\Delta J \approx 2\, e\, \Delta e$.
The same improvement of 0.1 point is a change of $J$ of $10^{-4}$ at $e = 5\%$,
but of $4\times10^{-4}$ at $e = 20\%$.

$e^*$ is bracketed by two quantities you already have:

$$
\sigma_{exp} \;\le\; e^* \;\le\; \sqrt{J(\theta_0)} .
$$

- **Lower bound.** Even a perfect model cannot fit the reference data better than
  their own scatter. Take the weighted RMS of the $\sigma_{exp,k}$ when they differ.
- **Upper bound.** The error at the starting point, read in the log of the first
  evaluation. The calibration can only improve on it.

Take $e^* = \sigma_{exp}$ when you trust the model form, i.e. when you expect the
calibrated model to fit the data to within the measurement scatter.
This is the conservative choice: a smaller $e^*$ gives tighter tolerances.
Take a value closer to $\sqrt{J(\theta_0)}$ when a model-form error is known to remain,
for instance a simulated curve that cannot reproduce a feature of the test.
If $\sqrt{J}$ at the end of the calibration differs from $e^*$ by more than a factor
of two, recompute the tolerances with the obtained value before any re-run.

**The sensitivity $S_j$.**
$S_j$ is the relative change of an output caused by a relative change of parameter $j$,
taken for the output that is most sensitive to $\theta_j$:

$$
S_j = \max_k \left\lvert \frac{\Delta y_k / y_k}{\Delta\theta_j / \theta_j} \right\rvert .
$$

$S_j = 1$ means that 1 % on the parameter gives 1 % on the output.
It is often known from the physics: a stiffness proportional to a modulus gives
$S = 1$, a force proportional to $\sqrt{G}$ gives $S = 0.5$.
Otherwise, compute it from two evaluations that differ by $\theta_j$ only,
for instance those of Section 3.4.
When nothing is known, take $S_j = 1$.

### 3.3 Rules

**Normalize the design space.**
Set ``normalize_design_space=True`` and give **finite bounds** to every parameter.
GEMSEO only normalizes the variables whose two bounds are finite.
For a variable with an infinite bound, ``init_step`` is a step in physical units,
which makes no sense for parameters of very different magnitudes,
such as a modulus of $10^5$ MPa and a toughness of $0.4$ N/mm.

**``init_step``: initial trust-region radius, in normalized units.**
COBYLA first evaluates the starting point, then moves each parameter by ``init_step``
in turn to build its first linear model.
The step must change $J$ well above the noise:

$$
\lvert J(\theta_0 + \mathrm{init\_step}) - J(\theta_0) \rvert \gtrsim 10\, \sigma_{num}.
$$

It must also stay within a physically reasonable neighbourhood of the start.
A value of 0.1 to 0.3, i.e. 10 % to 30 % of each range, is a good default.
An array can be given to use a different step for each parameter.

**``ftol_abs``: objective tolerance.**
Near the optimum $J \approx e^2$, so improving the relative error by $\Delta e$
changes $J$ by about $2 e^* \Delta e$.
The tolerance must also stay above the numerical noise, otherwise the criterion
never triggers:

$$
\mathrm{ftol\_abs} = \max\left(2\, e^* \, \Delta e,\; 3\, \sigma_{num}\right),
\qquad \mathrm{ftol\_rel} = 0 .
$$

If you prefer a relative criterion, ``ftol_rel`` $\approx 2\,\Delta e / e^*$ is equivalent.
With $\Delta e$ unknown, take $\Delta e = e^*/50$, i.e. ``ftol_rel`` $\approx 0.04$.

**``xtol_rel``: design tolerance.**
The reference data are uncertain, so the calibrated parameters are uncertain too.
A scatter $\sigma_{exp}$ on an output translates into a relative uncertainty on
parameter $j$ of about

$$
u_j \approx \frac{\sigma_{exp}}{S_j} .
$$

Locating the optimum much more precisely than $u_j$ is wasted effort.
Locating it to a tenth of $u_j$ is enough: the localization error then adds less
than 1 % to the parameter uncertainty, since uncertainties add in quadrature.
``xtol_rel`` is a single value that every parameter must satisfy,
so it is set by the best-determined parameter, i.e. the most sensitive one:

$$
\mathrm{xtol\_rel} = 0.1 \, \min_j u_j = 0.1 \, \frac{\sigma_{exp}}{\max_j S_j} .
$$

With $S_j$ unknown, take $S_j = 1$, i.e. ``xtol_rel`` $= 0.1\,\sigma_{exp}$:
5e-3 for a 5 % scatter.

The numerical noise sets a floor.
Below a relative parameter change of
$\frac{3\sigma_{num}}{2\, e^* \max_j S_j}$, the change of $J$ is lost in the noise,
and the iterates wander instead of converging.
If the rule above gives a smaller value, use this floor instead.

**``stop_crit_n_x``: window of the tolerance tests.**
The default $n+1$ is the minimum.
Use $n+2$ up to $2n+1$ when the model is noisy or a parameter is discrete,
so that a coincidence cannot stop the run.

**``stopval``: target value of the objective.**
Fitting the reference data better than their own scatter has no meaning.
With normalized metrics ($J \approx e^2$):

$$
\mathrm{stopval} = \sum_k w_k \, \sigma_{exp,k}^2 .
$$

If the target is out of reach, for instance because of a model-form error,
this criterion simply never triggers.

**``max_iter``: budget.**
COBYLA typically needs 10 to 20 evaluations per parameter.
Set ``max_iter`` to about $15n$, then check that the total cost
$\mathrm{max\_iter} \times t_{eval}$ is acceptable.
``max_iter`` is a safeguard: a well-tuned run should end on a tolerance
or on ``stopval``.

### 3.4 Estimating the numerical noise $\sigma_{num}$

**What the noise is.**
Model evaluations are deterministic: re-running the same point gives the same result,
and the cache returns it anyway.
But many models are not *smooth* functions of their parameters.
A tiny change of a parameter can make $J$ jump erratically around its true trend:

$$
J_{computed}(\theta) = J_{true}(\theta) + \varepsilon(\theta).
$$

Typical sources are:

- automatic time incrementation, which changes the number and position of the output
  points, hence the interpolation inside the metric;
- discrete events, such as cohesive elements failing one at a time, contact status
  changes, or plastic onset at integration points;
- convergence tolerances of the solver, and viscous or stabilization regularizations.

**Why it matters.**

- If $\varepsilon$ is larger than ``ftol_abs``, the objective test never triggers,
  and the run lasts until ``max_iter``.
- Once the trust region is so small that the true variation of $J$ between two points
  is of the order of $\varepsilon$, the slopes that COBYLA estimates are wrong.
  Further iterations then wander inside the noise and bring no real improvement.
- If the variation of $J$ produced by ``init_step`` is not large compared with
  $\varepsilon$, the first descent directions are already wrong.

**Protocol.**
It costs three to five evaluations, at the same discretization as the calibration.

1. Choose the starting point $\theta_0$.
   Perturb the parameter most likely to create noise, i.e. the one driving discrete
   events, by a small relative step $\delta$.
   Take $\delta \approx 10^{-3}$, small enough for the true curvature of $J$ to be
   negligible.
2. Evaluate $J_- = J(\theta_0 - \delta)$, $J_0 = J(\theta_0)$ and
   $J_+ = J(\theta_0 + \delta)$.
3. For a smooth function, the three values are aligned and the second difference is
   negligible. For a noise of standard deviation $\sigma_{num}$, the second difference
   has a standard deviation of $\sqrt{6}\,\sigma_{num}$. Hence:

    $$
    \sigma_{num} \approx \frac{\lvert J_+ - 2 J_0 + J_- \rvert}{\sqrt{6}} .
    $$

4. Check the result qualitatively.
   For a smooth function, $J_-$ and $J_+$ lie on either side of $J_0$.
   If both are above, or both below, with differences of the same order,
   the noise dominates.
5. Optionally, evaluate a fourth point $J(\theta_0 + \mathrm{init\_step})$ to check the
   ``init_step`` rule of Section 3.3.
   Its outputs, compared with those at $\theta_0$, also give the sensitivity $S_j$
   of Section 3.2.
   Do not compute $S_j$ from the $\pm\delta$ points: at such a small step,
   the noise dominates the difference.
   With more points, for instance $\pm\delta$ and $\pm 2\delta$, use the standard
   deviation of the residuals of a linear fit instead of the second difference.

Repeat the protocol for another parameter if they act through different mechanisms.

**If the noise is too large**, in order of efficiency:

1. Refine the discretization where the discrete events occur,
   for instance the mesh along the crack path.
2. Bound the maximum time increment, to get a more regular sampling of the outputs.
3. Otherwise, accept the noise: set ``ftol_abs`` to $3\sigma_{num}$.
   The resulting resolution on the relative error is
   $\Delta e \approx 3\sigma_{num} / (2e^*)$, and searching finer is useless.

## 4. Example

!!! note

    The values below are illustrative.
    They show how the rules of Section 3 combine; they are not recommended material data.

**Problem.**
A mode I delamination test (Double Cantilever Beam) is simulated by a finite-element
model with cohesive elements.
Three parameters are calibrated:

| Parameter | Start | Lower bound | Upper bound | Mainly drives |
|---|---|---|---|---|
| ``E1`` (MPa) | 110 000 | 70 000 | 160 000 | initial slope of the force-displacement curve |
| ``G1c`` (N/mm) | 0.40 | 0.20 | 1.00 | propagation force level, peak force |
| ``sigma1c`` (MPa) | 10 | 5 | 20 | shape of the peak |

The upper bound of ``sigma1c`` is chosen so that the cohesive zone stays resolved by
the mesh.

**Objective.**
The objective has two terms with equal weights:

- ``SBPISE`` on the force-displacement curve, with ``XYRange``, $w = 0.5$;
- ``RelativeMSE`` on the initial stiffness, $w = 0.5$.

The stiffness term pins ``E1``. Without it, ``E1`` and ``G1c`` compensate each other
on the peak force.

**What is known.**

| Quantity | Value | Origin |
|---|---|---|
| $\sigma_{exp}$ | 5 % on both outputs | scatter of repeated tests |
| $\Delta e$ | 0.1 point | engineering judgement |
| $S_{E_1}$ | 1 | the initial stiffness is proportional to ``E1`` |
| $S_{G_{Ic}}$ | 0.75 | beam theory: the propagation force varies as $G_{Ic}^{3/4}$ |
| $S_{\sigma_{Ic}}$ | 0.2 | estimated from two evaluations differing by ``sigma1c`` only |
| $t_{eval}$ | 10 min | one run |

**Expected error $e^*$.**
The first evaluation gives $J(\theta_0) = 5.0\times10^{-3}$, so
$5\,\% = \sigma_{exp} \le e^* \le \sqrt{5.0\times10^{-3}} = 7.1\,\%$.
The model form is trusted, so $e^* = \sigma_{exp} = 5\,\%$, the conservative end.

**Noise measurement.**
``G1c`` is perturbed by $\pm 0.2\%$ around 0.40, i.e. 0.3992, 0.4000 and 0.4008.
The three evaluations give:

$$
J_- = 4.91\times10^{-3}, \quad J_0 = 5.00\times10^{-3}, \quad J_+ = 5.12\times10^{-3}.
$$

The values are monotonic, which is the sign of a smooth function.
The noise is:

$$
\sigma_{num} \approx \frac{\lvert 5.12 - 10.00 + 4.91 \rvert \times 10^{-3}}{\sqrt{6}} \approx 1.2\times10^{-5}.
$$

A fourth evaluation at ``G1c`` $= 0.40 + 0.25 \times 0.80 = 0.60$ gives
$J = 9.1\times10^{-3}$.
The variation is $4\times10^{-3}$, far above $10\,\sigma_{num}$,
so ``init_step = 0.25`` is adequate.

**Settings.**

| Setting | Value | Rule |
|---|---|---|
| ``normalize_design_space`` | ``True`` | finite bounds on all parameters |
| ``init_step`` | 0.25 | $\Delta J = 4\times10^{-3} \gg 10\,\sigma_{num} = 1.2\times10^{-4}$ |
| ``ftol_abs`` | 1e-4 | $\max(2 \times 0.05 \times 0.001,\ 3 \times 1.2\times10^{-5}) = 10^{-4}$ |
| ``ftol_rel`` | 0 | absolute criterion used instead |
| ``xtol_rel`` | 5e-3 | $0.1 \times 0.05 / \max(1, 0.75, 0.2)$; above the noise floor $3 \times 1.2\times10^{-5} / (2 \times 0.05 \times 1) = 3.6\times10^{-4}$ |
| ``stop_crit_n_x`` | 5 | $n+2$, robustness to noise |
| ``stopval`` | 2.5e-3 | $0.5 \times 0.05^2 + 0.5 \times 0.05^2$ |
| ``max_iter`` | 50 | $\approx 15 n$; at most $1.5 \times 50 \times 10$ min $\approx$ 12.5 h |

```python
from gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings import NLOPT_COBYLA_Settings

from vimseo.tools.calibration.calibration_metrics import CalibrationMetricSettings
from vimseo.tools.calibration.calibration_metrics import CurveScaling
from vimseo.tools.calibration.calibration_step import CalibrationStepSettings

settings = CalibrationStepSettings(
    name_to_models={"DCB": model},
    control_outputs={
        "force_history": CalibrationMetricSettings(
            metric_name="SBPISE",
            mesh_name="displacement_history",
            scaling=CurveScaling.XYRange,
            weight=0.5,
        ).model_dump(),
        "initial_stiffness": CalibrationMetricSettings(
            metric_name="RelativeMSE",
            weight=0.5,
        ).model_dump(),
    },
    parameter_names=["E1", "G1c", "sigma1c"],
    optimizer_settings=NLOPT_COBYLA_Settings(
        normalize_design_space=True,
        init_step=0.25,
        ftol_abs=1e-4,
        ftol_rel=0.0,
        xtol_rel=5e-3,
        stop_crit_n_x=5,
        stopval=2.5e-3,
        max_iter=50,
    ),
)
```

**If the noise had been large.**
Suppose instead that the noise measurement had given
$J_- = 5.20\times10^{-3}$, $J_0 = 5.00\times10^{-3}$ and $J_+ = 5.30\times10^{-3}$.
Both neighbours are above $J_0$: the noise dominates.
The noise is then $\sigma_{num} \approx 5\times10^{-4}/\sqrt{6} \approx 2\times10^{-4}$.

- ``ftol_abs = 1e-4`` would be below the noise, and the run would last until ``max_iter``.
- Either refine the mesh along the crack path and measure the noise again,
  or set ``ftol_abs`` $= 3\sigma_{num} = 6\times10^{-4}$.
- In the second case, the resolution on the relative error is
  $\Delta e \approx 6\times10^{-4} / (2 \times 0.05) = 0.6$ point.
- The noise floor of ``xtol_rel`` becomes $6\times10^{-4} / (2 \times 0.05 \times 1)
  = 6\times10^{-3}$, above the $5\times10^{-3}$ given by the measurement scatter:
  set ``xtol_rel = 6e-3``.
  Parameter sets closer than 0.6 % cannot be told apart by this model.
