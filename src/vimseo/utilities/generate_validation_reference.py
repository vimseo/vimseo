# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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
"""
Generate reference data from a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd
from gemseo.datasets.io_dataset import IODataset

from vimseo.tools.doe.custom_doe import CustomDOETool

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from gemseo.datasets.dataset import Dataset
    from numpy import ndarray
    from pandas import DataFrame

    from vimseo.core.base_integrated_model import IntegratedModel


@dataclass
class Bias:
    mult_factor: float = 1.0
    shift: float = 0.0
    component: int | Iterable[int] = 0


def generate_reference_from_dataset(
    model: IntegratedModel,
    input_dataset: Dataset,
    df: DataFrame | None = None,
    specific_inputs: Mapping[str, ndarray] | None = None,
    input_names: Iterable[str] = (),
    output_names: Iterable[str] = (),
    outputs_to_bias: Mapping[str, Bias] | None = None,
    additional_name_to_data: Mapping[str, ndarray] | None = None,
    as_dataset=False,
):
    """Generate artificial experimental data from input data and a model.

    Output data can be biased.
    """
    outputs_to_bias = {} if outputs_to_bias is None else outputs_to_bias
    if specific_inputs is not None:
        model.default_input_data.update(specific_inputs)

    dataset = (
        CustomDOETool()
        .execute(
            model=model,
            input_dataset=input_dataset,
            input_names=input_names,
            output_names=(
                output_names if len(output_names) > 0 else model.get_output_data_names()
            ),
        )
        .dataset
    )
    for output_name, bias in outputs_to_bias.items():
        if isinstance(bias.component, int):
            dataset.loc[:, ("outputs", output_name, bias.component)] = dataset.loc[
                :, ("outputs", output_name, bias.component)
            ].apply(
                lambda x: x * bias.mult_factor + bias.shift  # noqa: B023
            )  # noqa: B023
        else:
            for i in bias.component:
                dataset.loc[:, ("outputs", output_name, i)] = dataset.loc[
                    :, ("outputs", output_name, i)
                ].apply(
                    lambda x: x * bias.mult_factor + bias.shift  # noqa: B023
                )  # noqa: B023
    if not as_dataset:
        df_ = dataset.copy()
        df_.columns = dataset.get_columns()
        df_.dropna(inplace=True)
        if additional_name_to_data is not None:
            for additional_name, data in additional_name_to_data.items():
                df_[additional_name] = data
        if df is not None:
            return pd.concat([df, df_], ignore_index=True)
        return df_
    if df is not None:
        msg = "Concatenation on datasets is not handled."
        raise ValueError(msg)
    return dataset


def generate_reference_from_parameter_space(
    model, parameter_space, n_samples, **options
):
    """Create a reference data by sampling a model on a parameter space."""
    input_data = parameter_space.compute_samples(n_samples=n_samples, as_dict=False)
    reference_data = IODataset()
    reference_data.add_group(
        IODataset.INPUT_GROUP,
        input_data,
        parameter_space.uncertain_variables,
    )

    # Reference data is a GEMSEO Dataset:
    return generate_reference_from_dataset(model, reference_data, **options)
