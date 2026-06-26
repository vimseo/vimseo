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

"""A verification result and verification case description.."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from json import dumps
from typing import TYPE_CHECKING
from typing import ClassVar

from vimseo.tools.base_tool import BaseResult
from vimseo.utilities.json_grammar_utils import EnhancedJSONEncoder

if TYPE_CHECKING:
    from gemseo.datasets.dataset import Dataset
    from pandas import DataFrame

    from vimseo.core.model_description import ModelDescription

CASE_DESCRIPTION_TYPE = Mapping[str, str | list[str]]


@dataclass
class VerificationResult(BaseResult):
    """The result of a verification of a model."""

    _PREFIX_KEY: ClassVar[str] = "reference_name"

    simulation_and_reference: Dataset | None = None
    """A Dataset containing the input variables (where the model is executed), the model
    output variables and the reference output variables."""

    element_wise_metrics: Dataset | None = None
    """A Dataset containing the input variables and the metrics comparing the reference
    outputs with the model outputs."""

    integrated_metrics: Mapping[str, Mapping[str, float]] | None = None
    """A dictionary mapping variable names and metric names to integrated metric
    values."""

    description: CASE_DESCRIPTION_TYPE = field(default_factory=dict)
    """A description of the verification case."""

    def _fill_metadata(
        self,
        case_description: CASE_DESCRIPTION_TYPE | None,
        model_description: ModelDescription,
    ):
        """Fill the metadata related to Verification."""
        if case_description:
            self.description = case_description
        self.metadata.model = model_description

    def __str__(self):
        from gemseo.utils.string_tools import MultiLineString

        text = MultiLineString()
        text.add(
            dumps(self.metadata, sort_keys=True, indent=4, cls=EnhancedJSONEncoder)
        )
        text.add("Integrated metrics:")
        text.indent()
        for k, v in self.integrated_metrics.items():
            text.add(f"{k}: {v}")
        text.dedent()
        text.add("Element-wise metrics:")
        text.add(repr(self.element_wise_metrics))
        text.add("")
        text.add("Simulation and references:")
        text.add(repr(self.simulation_and_reference))
        text.add("")
        return str(text)


@dataclass
class SolutionVerificationResult(VerificationResult):
    """The result of a convergence verification of a model."""

    cross_validation: dict = field(default_factory=dict)
    """The cross validation on the extrapolated quantities."""

    extrapolation: dict = field(default_factory=dict)
    r"""The extrapolated quantities and associated uncertainty.

    Uncertainty is expressed as the median absolute deviation (MAD). A 95% confidence
    interval, assuming a normal distribution for q and beta, is obtained with $median \pm
    2 MAD$. The Relative Discretization Error (RDE) is given from the finest to the
    coarsest mesh.
    """

    # TODO implement value in execute()
    error_default_element_size: Mapping[str, float] = field(default_factory=dict)
    """The error metrics for the default element size."""

    def __str__(self):
        from gemseo.utils.string_tools import MultiLineString

        text = MultiLineString()
        text.add(super().__str__())
        text.add("Richardson extrapolation:")
        text.add(repr(self.extrapolation))
        text.add("")
        text.add("Cross validation on Richardson extrapolation:")
        text.add(repr(self.cross_validation))
        return str(text)


class SolutionVerificationCaseResult(BaseResult):
    """A result from a solution verification case."""

    convergence_data: DataFrame | None = None
    """A DataFrame containing the convergence data used for the verification."""
