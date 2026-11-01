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

"""Plots of the verification analysis nodes."""

from __future__ import annotations

from vimseo.analysis_nodes.post_analysis_nodes.verification_plots.convergence_cross_validation import (
    ConvergenceCrossValidationPlotter,
)
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots.convergence_fit import (
    ConvergenceFitPlotter,
)
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots.error_metric_histogram import (
    ErrorMetricHistogramPlotter,
)
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots.error_versus_element_size import (
    ErrorVersusElementSizePlotter,
)
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots.relative_error_versus_cpu_time import (
    RelativeErrorVersusCpuTimePlotter,
)
from vimseo.analysis_nodes.post_analysis_nodes.verification_plots.relative_error_versus_element_size import (
    RelativeErrorVersusElementSizePlotter,
)

__all__ = [
    "ConvergenceCrossValidationPlotter",
    "ConvergenceFitPlotter",
    "ErrorMetricHistogramPlotter",
    "ErrorVersusElementSizePlotter",
    "RelativeErrorVersusCpuTimePlotter",
    "RelativeErrorVersusElementSizePlotter",
]
