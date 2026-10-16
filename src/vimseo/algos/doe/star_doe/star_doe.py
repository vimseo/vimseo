# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
r"""The DOE used by a star One-factor-at-a-Time (OAT) sensitivity analysis.

From a center :math:`x_0`,
the star DOE varies each component :math:`i` of the variables
by a physical step :math:`h_i` while the other components remain at the center:

.. math::

   x_0,\ x_0+h_1e_1,\ \ldots,\ x_0+h_de_d
   \quad\left[,\ x_0-h_1e_1,\ \ldots,\ x_0-h_de_d\right]

where the points in brackets are added when the DOE is two-sided.

Contrary to the GEMSEO ``OATDOE``,
whose points form a trajectory (the steps accumulate from a point to the next one)
and whose step is defined in the unit hypercube
(i.e. in probability for a random variable),
all the effects are measured around the same center
and the step is defined in the physical space,
whatever the probability distribution of the variable.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import ClassVar

from gemseo.algos.doe.base_doe_library import BaseDOELibrary
from gemseo.algos.doe.base_doe_library import DOEAlgorithmDescription
from gemseo.algos.parameter_space import ParameterSpace
from numpy import abs as np_abs
from numpy import apply_along_axis
from numpy import atleast_1d
from numpy import concatenate
from numpy import diag
from numpy import flatnonzero
from numpy import isfinite
from numpy import vstack

from vimseo.algos.doe.star_doe.settings.star_doe_settings import StarDOE_Settings

if TYPE_CHECKING:
    from gemseo.algos.design_space import DesignSpace
    from gemseo.typing import RealArray

LOGGER = logging.getLogger(__name__)


class StarDOE(BaseDOELibrary[StarDOE_Settings]):
    """The DOE used by a star One-factor-at-a-Time sensitivity analysis."""

    _USE_UNIT_HYPERCUBE: ClassVar[bool] = False

    ALGORITHM_INFOS: ClassVar[dict[str, DOEAlgorithmDescription]] = {
        "StarDOE": DOEAlgorithmDescription(
            algorithm_name="StarDOE",
            description="The DOE used by a star One-factor-at-a-Time sensitivity "
            "analysis.",
            internal_algorithm_name="StarDOE",
            library_name="StarDOE",
            Settings=StarDOE_Settings,
        )
    }

    def __init__(self, algo_name: str = "StarDOE") -> None:
        super().__init__(algo_name)

    def _generate_unit_samples(self, design_space: DesignSpace) -> RealArray:
        """
        Raises:
            ValueError: When a point of the star is outside the bounds of the
                variables space.
        """
        center = self.__get_center(design_space)
        steps = self.__get_steps(design_space, center)
        points = [center, *(center + diag(steps))]
        if self._settings.two_sided:
            points.extend(center - diag(steps))

        samples = vstack(points)
        self.__check_bounds(design_space, samples)
        return apply_along_axis(design_space.transform_vect, axis=1, arr=samples)

    def __get_center(self, design_space: DesignSpace) -> RealArray:
        """Return the center of the star.

        Args:
            design_space: The variables space.

        Returns:
            The center of the star.
        """
        center = dict(self._settings.center)
        unknown_names = set(center).difference(design_space.variable_names)
        if unknown_names:
            msg = (
                f"The variables {sorted(unknown_names)} of the center of the star "
                f"are not in the variables space, whose variables are "
                f"{design_space.variable_names}."
            )
            raise ValueError(msg)

        # The current value of a random variable is not used,
        # since a DOE sets it to its best sample.
        for name in design_space.variable_names:
            if name in center:
                continue

            if (
                isinstance(design_space, ParameterSpace)
                and name in design_space.uncertain_variables
            ):
                center[name] = design_space.distributions[name].mean
            else:
                center[name] = design_space.get_current_value(variable_names=[name])

        return concatenate([
            atleast_1d(center[name]).astype(float)
            for name in design_space.variable_names
        ])

    def __get_steps(self, design_space: DesignSpace, center: RealArray) -> RealArray:
        """Return the physical steps of the components of the variables.

        The step of a component is relative to its center.
        A zero center would give a zero step:
        the step of such a component is relative to its scale instead,
        or is the fallback step if it has no scale.

        Args:
            design_space: The variables space.
            center: The center of the star.

        Returns:
            The physical steps.
        """
        relative_step = self._settings.relative_step
        steps = relative_step * np_abs(center)
        zero_center_components = flatnonzero(center == 0)
        if not zero_center_components.size:
            return steps

        scales = self.__get_scales(design_space)
        component_names = self.__get_component_names(design_space)
        for i in zero_center_components:
            scale, scale_origin = scales[i]
            if scale is None:
                steps[i] = self._settings.fallback_step
                step_origin = "the fallback step, as it has no scale"
            else:
                steps[i] = relative_step * scale
                step_origin = scale_origin

            LOGGER.warning(
                "The center of %s is zero; its step %s is computed from %s.",
                component_names[i],
                steps[i],
                step_origin,
            )

        return steps

    @staticmethod
    def __get_scales(design_space: DesignSpace) -> list[tuple[float | None, str]]:
        """Return the scales of the components of the variables.

        The scale of a component is the standard deviation of its distribution
        if the variable is random,
        otherwise the range of its bounds if both are defined and different.

        Args:
            design_space: The variables space.

        Returns:
            The scale of each component, ``None`` if it has no scale,
            and the origin of this scale.
        """
        names = design_space.variable_names
        upper_bounds = design_space.get_upper_bounds(names)
        ranges = upper_bounds - design_space.get_lower_bounds(names)
        scales = []
        for name in names:
            indices = design_space.get_variables_indexes([name])
            if (
                isinstance(design_space, ParameterSpace)
                and name in design_space.uncertain_variables
            ):
                values = atleast_1d(design_space.distributions[name].standard_deviation)
                values = values.repeat(indices.size) if values.size == 1 else values
                origin = "the standard deviation of its distribution"
                scales.extend((float(value), origin) for value in values)
            else:
                # A zero range would give a zero step.
                scales.extend(
                    (float(ranges[i]), "the range of its bounds")
                    if isfinite(ranges[i]) and ranges[i] > 0
                    else (None, "")
                    for i in indices
                )

        return scales

    @staticmethod
    def __get_component_names(design_space: DesignSpace) -> list[str]:
        """Return the names of the components of the variables.

        Args:
            design_space: The variables space.

        Returns:
            The names of the components, e.g. ``"x[1]"`` for a vector variable.
        """
        component_names = []
        for name in design_space.variable_names:
            size = design_space.get_size(name)
            if size == 1:
                component_names.append(name)
            else:
                component_names.extend(f"{name}[{i}]" for i in range(size))

        return component_names

    def __check_bounds(self, design_space: DesignSpace, samples: RealArray) -> None:
        """Check that the points of the star are inside the defined bounds.

        Args:
            design_space: The variables space.
            samples: The points of the star.

        Raises:
            ValueError: When a point of the star is outside the defined bounds.
        """
        names = design_space.variable_names
        lower_bounds = design_space.get_lower_bounds(names)
        upper_bounds = design_space.get_upper_bounds(names)
        outside = ((samples < lower_bounds) | (samples > upper_bounds)).any(axis=0)
        if outside.any():
            component_names = self.__get_component_names(design_space)
            msg = (
                "The star DOE goes outside the bounds of "
                f"{[component_names[i] for i in outside.nonzero()[0]]}; "
                "reduce the relative step or move the center."
            )
            raise ValueError(msg)
