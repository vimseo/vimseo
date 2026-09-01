<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Tan model validity

Tan's model is based on an elastic approximation.
However, when damage occurs (matrix cracking, and possibly later some fibers failure), there are some local stress redistributions and the considered linear elastic law b
becomes invalid locally. Engineers use the "point-stress" method,
as a correction of basic linear-elastic results, in order to estimate the occurence of substancial damage propagation (fibre failure). This method consists in observing the
stress value (computed from a fully elastic structure) at a distance 'd_0' from the hole ("point-stress distance"), instead of the direct vicinity of the hole. Despite some physical meaningfulness of 'd_0', its value is actually identified from tests and it is highly sensitive to many parameters
(material ply properties, layup, size of the hole, etc).
The geometry corresponding to this new configuration is illustrated in the following
figure:

![Validity zone of Tan model for the point stress approximation](../../images/images_tan/tan_validity_zone.png)

In the previous figure, the stripped area is where the computed stress is ignored, for estimation of damage occurence. Note that for a critical loading, it also matches approximately where the elastic model is no longer valid

## Reserve factor

Following the point-stress method, the fibre-direction failure criterion is evaluated
over the valid zone only, $r \geq R + d_0$:

$$
\mathrm{crit} = \max\left(\frac{\sigma_{xx}}{X_t}, \frac{-\sigma_{xx}}{X_c}\right)
$$

that is $\sigma_{xx} / X_t$ where the laminate is in tension and $|\sigma_{xx}| / X_c$
where it is in compression, $X_t$ and $X_c$ being the longitudinal tensile and
compressive strengths of the ply. Failure is reached at $\mathrm{crit} = 1$. Inside
the ignored zone $r < R + d_0$ -- the stripped area of the figure above -- the criterion
is undefined and returned as `nan`.

The reserve factor is the inverse of the maximum of the criterion over the valid zone:

$$
\mathrm{RF} = \frac{1}{\max(\mathrm{crit})}
$$

The criterion reaches its extrema on the circle $r = R + d_0$, the boundary of the
ignored zone. In order to read them exactly rather than to interpolate them from the
Cartesian grid on which the stress field is evaluated, the criterion is output on a
dedicated mesh whose nodes are those of the grid plus a set of nodes lying exactly on
that circle. Those additional nodes make the mesh unstructured (it is triangulated), so
the criterion is written to its own file, `criterion.vtk`, while the stress field keeps
its structured grid in `flux.vtk`. The reserve factor is therefore independent of the
`grid_resolution` input.

In the model outputs, both quantities are available in two forms. As **fields**, on the
enriched mesh written to `criterion.vtk`, where they are defined outside the ignored
zone only. As **scalars**, `crit` and `reserve_factor`, which are the critical values of
those fields over the valid zone: `crit` is the maximum of the criterion field, and
`reserve_factor` is the minimum of the reserve factor field. The two statements are
equivalent, the criterion being non-negative:

$$
\min_{r \geq R + d_0} \mathrm{RF} = \frac{1}{\max_{r \geq R + d_0} \mathrm{crit}}
$$

so there is no separate "minimum reserve factor" output: `reserve_factor` already is it.

## Example of results

![Example of stress field obtained with Tan model](../../images/images_tan/tan_fields.png)
