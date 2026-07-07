<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->



## Set up a parameter space

A space of uncertain parameters is an input to several tools in VIMSEO:
for instance a sensitivity analysis, a DOE, a model to model code verification.
Setting up a parameter space with a large number of variables requires to
specify a large number of options.
In VIMSEO, the tool in charge of generating a parameter space
is the so called ``SpaceTool``.
The variables are in general treated by groups.
For example, the first group has a normal distribution
centered on the model default value,
and second group has a uniform distribution spanning the entire variable range.
The ``SpaceTool`` allows to set up a parameter space by successive updates.
At each update, a list of variables, a ``SpaceBuilder``
and its settings can be selected.
Four ``SpaceBuilder`` are available:
  - ``FromModelCenterAndCov``: suited to set up distributions based on model default values
    and a coefficient of variation. Note that the center of the distribution can be chosen
    based on a relationship between the minimum and maximum bounds of the variable,
    but it requires that both bounds are defined.
  - ``FromModelMinAndMax``: suited to set up distributions from the bounds of the variables
    if both bounds are defined.
  - ``FromCenterAndCov``
  - ``FromMinAndMax``

The last two are agnostic of the model.

Even if this process can be performed programmatically,
being able to visualize the chosen distributions and how they are located
with respect to the model bounds is very useful.
Indeed, the distributions can be truncated by the bounds and, for example,
a triangular distribution may have a shape very different from the expected one.

As a result, VIMSEO has a dedicated dashboard to set up a parameter space.
The dashboard can be displayed by typing ``dashboard_space`` in a console
where VIMSEO is installed.
The following inputs can be used to initialize the parameter space:
  - a model
  - a ``SpaceTool`` result
  - a material values ``JSON`` file

If the model is the input, the parameter space can be initialized to the model material
by ticking the checkbox ``From model material``.
Only the variables for which probability distributions are defined will be
considered to build the parameter space.

![](input_data.PNG)

For VIMSEO beam models, the default material defines probability distributions
for the

![](beam_default_material.PNG)

As explained above, the parameter space can then be updated
by first selecting in the sidebar the variables to modify:

![](variable_selection.PNG)

Then the ``SpaceBuilder`` must be chosen, and its settings:

![](from_model_center_and_cov.PNG)

Then the ``Submit space parameters`` must be clicked.

The process of selecting variables, a space builer and its settings
and validating by clicking the ``Submit space parameters`` can be repeated
until the user is satisfied with the parameter space.

!!! note

    To avoid setting distributions whose support is outside the model bounds,
    the model bounds can be shown by ticking the ``Show model bounds`` checkbox
    at the bottom of the sidebar.
    The part of the distribution which is outside the bounds is shown
    by a vertical red band.

The parameter space can finally be downloaded as a ``JSON`` file.
