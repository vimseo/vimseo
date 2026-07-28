<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->




## Verification of the Opfm material law

TODO replace OpfmCUbe by OpfmUnitcell

To verify that the expected model form is correctly implemented, the ``OpfmCube`` model is used.
Indeed, this model uses the same ``run-processor`` processor component (and thus the same material subroutine)
as the ``OpfmPlate`` model.
It differs from the latter by its ``pre-processor`` and ``post-processor`` components, in which an RVE approach
is used instead of a meshed model of a plate.
Thus, it allows the verification of the implementation of the model dataflow, the call to ``Abaqus`` with proper options,
and the interfacing with the subroutine.
The verification is based on the relationship between the material properties defined as inputs
and the model's outputs such as max_strength. For instance, when considering the response
simulated with the OpfmCube model under a pure longitudinal load (PST on 0° laminate),
the material property Xt should be equal to the max_strength output.
The code verification relies on the VIMSEO ``CodeVerificationAgainstData`` tool, where an example is given
[here](http://docvimscomposites.ipf7135.irt-aese.local/generated/examples/code_verification/plot_opfm_cube_pst0_vs_data.html).

The error between ``Xt`` and ``max_strength`` is computed for two values of the numerical
parameter ``nb_intervals``, which controls the convergence of the subroutine.
The reference dataset that needs to be specified to the ``CodeVerificationAgainstData`` tool
is composed of three variables:
  - the inputs ``Xt`` and ``nb_intervals``
  - the output ``max_strength``

Several metrics of comparison can be specified to evaluate the error between the reference output
and the corresponding simulated value.

![](opfm_cube_pst_code_verification.PNG)

Here, the relative error is found to be negligible.


## Matrix

{{ read_csv('code_verification_matrix.csv', sep=";", index_col=0) }}


## Verification of the integration of the Opfm material law with Abaqus

Repeat above verif for OpfmCUbe

Then, the integration of the Opfm law with Abaqus, which is done through VIMSEO
``RunAbaqusWrapper`` can be performed.
First, we can check that the OpfmCube and OpfmUnitCell models return results that are close
on load cases with uniform stress distribution.
By close, we mean $10 \%$ error, because the boundary conditions between the two
models are not strictly the same.

TODO add link to deployed doc


## Code verification for OpfmPlate model PST

Secondly, we can check that the OpfmPlate and OpfmCube model also return close results.

The following test matrix is used:

{{ read_csv('code_verification_opfm_matrix.csv', sep=";") }}

The OpfmPlate PST model is verified against OpfmCube PST.
The variables of the parameter space on which the models are sampled
correspond to input variables to which the ``max_strength`` output
is the most sensitive for the OpfmCube PST model, which are:

  - $E1$
  - $E1t$
  - $G12$
  - $Xt$

The geometrical parameters:

 - $width$
 - $length$
 - $thickness$

are also added. Triangular distributions are defined for each variable,
ranging over the bounds defined in the Opfm material of ``vims-composites``.

TODO link to example

#### Layup $[0]$

The input parameter space is represented in the following figure:
![](code_verification_opfm_plate_pst_input_space.png)

One way to represent how the error range and their distribution
is to plot a histogram of the errors (one for each error metric).
Thus, in abscissa we have error band values, and in ordinate
we have the number of error values within a given band.
We observe that the relative error on $max\_strength$ between the two models
can reach $10 \%$:
![](code_verification_opfm_plate_pst_error_histogram.png)
