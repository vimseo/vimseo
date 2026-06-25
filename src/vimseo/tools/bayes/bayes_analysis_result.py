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

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gemseo.third_party.prettytable.prettytable import PrettyTable
from gemseo.utils.string_tools import MultiLineString

from vimseo.tools.base_tool import BaseResult

if TYPE_CHECKING:
    from numpy import ndarray
    from openturns import DeconditionedDistribution

LOGGER = logging.getLogger(__name__)


@dataclass
class BayesAnalysisResult(BaseResult):
    """The result of a Bayesian inference."""

    raw_samples: ndarray | None = None
    """The MCMC samples without burnin or thining."""

    thin_number: int | None = None
    """The thining number to ensure independency between the posterior samples."""

    ndim: int | None = None
    """The dimension of the calibration problem."""

    processed_samples: ndarray | None = None
    """The MCMC samples after burnin or thining."""

    posterior_predictive: DeconditionedDistribution | None = None
    """The posterior predictive distribution useful to perform uncertainty
    propagation."""

    lppd: float = None
    """Twice the opposite of the lppd, a Bayesian validation criterion."""

    ml: float = None
    """Twice the opposite of the log marginal likelihood, a Bayesian validation
    criterion."""


@dataclass
class PosteriorChecks:
    lppd: float
    """Twice the opposite of the lppd, a Bayesian validation criterion."""

    ml: float
    """Twice the opposite of the log marginal likelihood, a Bayesian validation
    criterion."""

    model: str
    """The model whose results are to be plotted."""

    posterior_predictive: DeconditionedDistribution
    """The posterior predictive distribution useful to perform uncertainty
    propagation."""

    def __init__(self, result: BayesAnalysisResult) -> None:

        self.ml = result.ml

        self.lppd = result.lppd

        self.posterior_predictive = result.posterior_predictive

        self.model = result.metadata.settings["likelihood_dist"]

    def __str__(self):
        text = MultiLineString()
        text.add("Bayesian verification indices for " + self.model + " model.")

        table = PrettyTable(["lppd", "ml"])

        table.add_row([
            self.lppd,
            self.ml,
        ])
        text.add(table.get_string())
        return str(text)
