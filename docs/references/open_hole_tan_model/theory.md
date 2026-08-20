<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Theory - Open Hole Plate

## Introduction

The **Tan model** provides an analytical formulation for computing membrane stress
fields in an infinite orthotropic plate with a circular hole.

![Geometrical variables describing the open hole geometry](../../images/images_tan/open_hole_setup.png)

### Assumptions

1. The plate is considered infinite
2. The material behaviour is linear elastic orthotropic
3. The loading is planar

### Units

Geometric inputs (`length`, `width`, `radius`, `d0`, `thickness`) are expressed
in mm. The ply material (moduli, strengths -- see
[Materials](../materials/index.md)) is expressed in MPa, and so is the applied
`load` and the resulting stress outputs (`sigma_xx`, `sigma_yy`, `sigma_xy`,
`sigma_xx_r`, `sigma_xx_d0`).

### Multiaxial loading

The applied load is defined as:

```
N = (Nxx, Nyy, Nxy)
```

![Application of multi-axial loading](../../images/images_tan/open_hole_multiaxial_loading.png)

The model relies on the **principle of superposition**: the response to multiaxial
loading can be decomposed into the sum of responses to each load component.
