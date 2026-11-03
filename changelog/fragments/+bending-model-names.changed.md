<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

**Breaking change.** The inputs and outputs of `BendingTestAnalytical` are renamed, together with those of `BendingBeamFem` in vimseo-abaqus, so that both models are still compared by name: the vectors along the beam axis are suffixed by `_profile`, and their positions are named `position_profile_for_<quantity>`. Rename `imposed_dplt` into `imposed_displacement`, `relative_dplt_location` into `relative_load_location`, `dplt` into `deflection_profile`, `dplt_grid` into `position_profile_for_deflection`, `moment` into `moment_profile`, `moment_grid` into `position_profile_for_moment`, `maximum_dplt` into `maximum_deflection`, `location_max_dplt` into `location_max_deflection`, `dplt_at_force_location` into `deflection_at_load_point`, and the outputs of the pre-processors `quadratic_moment` into `second_moment_of_area` and `imposed_dplt_location` into `load_location`. The boundary condition variables of the `Beam_*` load cases are renamed accordingly. The plots are named after the new names, e.g. `deflection_profile_vs_position_profile_for_deflection`. The results archived before this change keep the former names.

`maximum_deflection` is zero, no longer NaN, when the deflection is zero everywhere.
