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

"""A squared-error metric."""

from __future__ import annotations

from typing import TypeVar

from gemseo.typing import NumberArray
from gemseo.utils.metrics.base_metric import BaseMetric
from numpy import absolute
from numpy import isnan
from numpy import mean
from numpy import nanmean
from numpy import nanstd
from scipy.stats import wasserstein_distance

from vimseo.utilities.metrics import EPSILON

_InputT = TypeVar("_InputT", float | int | complex, NumberArray)


class RelativeSquaredErrorMetric(BaseMetric[_InputT, _InputT]):
    """A relative squared error metric.

    The squared error is divided by the absolute value of ``a``.
    """

    @staticmethod
    def compute(a: _InputT, b: _InputT) -> _InputT:  # noqa: D102
        return (a - b) ** 2 / (absolute(a) + EPSILON)


class AbsoluteErrorMetric(BaseMetric[_InputT, _InputT]):
    """The absolute difference between ``a`` and ``b``."""

    @staticmethod
    def compute(a: _InputT, b: _InputT) -> _InputT:  # noqa: D102
        return absolute(a - b)


class RelativeErrorMetric(BaseMetric[_InputT, _InputT]):
    """A relative absolute error metric.

    The absolute value of ``a - b`` divided by the absolute value of ``b``.
    """

    @staticmethod
    def compute(a: _InputT, b: _InputT) -> _InputT:  # noqa: D102
        return absolute(a - b) / (absolute(b) + EPSILON)


class AreaMetric(BaseMetric[_InputT, _InputT]):
    """The area (also called Wasserstein) metric."""

    @staticmethod
    def compute(a: _InputT, b: _InputT) -> _InputT:  # noqa: D102
        a = a[~isnan(a)]
        b = b[~isnan(b)]
        return wasserstein_distance(a, b)


class RelativeAreaMetric(BaseMetric[_InputT, _InputT]):
    """The relative area (also called Wasserstein) metric.

    The area metric divided by the absolute mean value of ``b``.
    """

    @staticmethod
    def compute(a: _InputT, b: _InputT) -> _InputT:  # noqa: D102
        a = a[~isnan(a)]
        b = b[~isnan(b)]
        return wasserstein_distance(a, b) / (abs(mean(b)) + EPSILON)


class RelativeMeanToMean(BaseMetric[_InputT, _InputT]):
    """The relative difference between mean simulated value and mean reference value.

    This difference is divided by the absolute mean value of ``b``.
    """

    @staticmethod
    def compute(a: _InputT, b: _InputT) -> _InputT:  # noqa: D102
        return abs(mean(a) - mean(b)) / (abs(mean(b)) + EPSILON)


class AbsoluteRelativeErrorP90(BaseMetric[_InputT, _InputT]):
    """The relative difference between simulated PDF and reference PDF.

    This difference is divided by the mean value of ``b``.
    It assumes normality of the two populations.
    It is interpreted as the fact that there is 90% chance that the error is less
     than the metric value.
    """

    @staticmethod
    def compute(a: _InputT, b: _InputT) -> _InputT:  # noqa: D102
        return (
            abs(nanmean(a) - nanmean(b))
            + 1.645 * (nanstd(a) ** 2 + nanstd(b) ** 2) ** 0.5
        ) / (abs(nanmean(b)) + EPSILON)
