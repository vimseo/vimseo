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

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import array
from numpy import full
from numpy import vstack

from vimseo.api import create_model
from vimseo.problems import beam_analytic
from vimseo.tools.doe.custom_doe import CustomDOETool
from vimseo.utilities.datasets import SEP
from vimseo.utilities.datasets import plot_dataset_element

if TYPE_CHECKING:
    from collections.abc import Mapping

imposed_dplt = [5.0, 5.0, 5.0, 10.0, 10.0]
young_modulus = array([200000.0, 200000.0, 200000.0, 200000.0, 200000.0])
width = array([10.0, 10.0, 10.0, 10.0, 10.0])
height = array([10.0, 15.0, 20.0, 15.0, 20.0])
length = array([1000.0, 1000.0, 1000.0, 1000.0, 1000.0])
relative_support_location = full((5, 2), [0.0, 1.0])
support_length = array([600.0, 600.0, 600.0, 600.0, 600.0])
relative_dplt_location = array([0.5, 0.5, 0.5, 0.5, 0.5])

data = vstack((
    imposed_dplt,
    young_modulus,
    width,
    height,
    length,
    relative_support_location.T,
    relative_dplt_location,
)).transpose()
data_names = [
    "imposed_dplt",
    "young_modulus",
    "width",
    "height",
    "length",
    "relative_support_location",
    "relative_dplt_location",
]
data_group = {
    "imposed_dplt": IODataset.INPUT_GROUP,
    "young_modulus": IODataset.INPUT_GROUP,
    "width": IODataset.INPUT_GROUP,
    "height": IODataset.INPUT_GROUP,
    "length": IODataset.INPUT_GROUP,
    "relative_support_location": IODataset.INPUT_GROUP,
    "relative_dplt_location": IODataset.INPUT_GROUP,
}
variable_names_to_n_components = {
    "imposed_dplt": 1,
    "young_modulus": 1,
    "width": 1,
    "height": 1,
    "length": 1,
    "relative_support_location": 2,
    "relative_dplt_location": 1,
}

INPUT_DATASET = Dataset.from_array(
    data,
    variable_names=data_names,
    variable_names_to_group_names=data_group,
    variable_names_to_n_components=variable_names_to_n_components,
)


def create_dataset_from_beam_model(input_dataset):
    datasets = {}
    for load_case in ["Cantilever", "ThreePoints"]:
        beam_model = create_model("BendingTestAnalytical", load_case)
        doe = CustomDOETool()
        input_names = input_dataset.get_variable_names(group_name=IODataset.INPUT_GROUP)
        input_names.remove("relative_support_location")
        doe.execute(beam_model, input_dataset, input_names=input_names)
        doe.result.dataset.to_csv(
            f"bending_test_analytical_{load_case.lower()}.csv", sep=SEP
        )
        datasets[load_case] = doe.result.dataset
    return datasets


DEFAULT_DATASETS = {
    "Cantilever": IODataset(
        Dataset.from_csv(
            Path(beam_analytic.__file__).parent
            / "bending_test_analytical_dataset_cantilever.csv",
            delimiter=SEP,
            first_column_as_index=True,
        )
    ),
    "ThreePoints": IODataset(
        Dataset.from_csv(
            Path(beam_analytic.__file__).parent
            / "bending_test_analytical_dataset_threepoints.csv",
            delimiter=SEP,
            first_column_as_index=True,
        )
    ),
}


# TODO remove and use the logic directly
def bending_test_analytical_reference_dataset(
    datasets: Mapping[str:Dataset] | None = None,
    mult_factor: float = 1.0,
    shift: float = 0.0,
) -> Mapping[str:Dataset]:
    """Creates datasets for validation of cantilever and three point bending load cases.

    Args:
        datasets: A dictionary of datasets mapping load case name with a dataset
            containing the input variables for the ``BendingTestAnalytical``.
            If ``None``, use default datasets.
        mult_factor: The multiplication factor applied to the reaction force.
        shift: The shift added to the reaction force.

    Returns: dict of gemseo :class:`Dataset`
    """
    if not datasets:
        datasets = deepcopy(DEFAULT_DATASETS)
    for dataset in datasets.values():
        dataset.loc[:, ("outputs", "reaction_forces", 0)] = dataset.loc[
            :, ("outputs", "reaction_forces", 0)
        ].apply(lambda x: x * mult_factor + shift)
    return datasets


if __name__ == "__main__":
    datasets = create_dataset_from_beam_model(INPUT_DATASET)
    abscissa_variable = "dplt_grid"
    variables = ["dplt"]
    for load_case, dataset in datasets.items():
        plot_dataset_element(
            dataset,
            0,
            variables,
            abscissa_variable,
            file_name=f"reference_bending_test_analytical_{load_case}_{variables}_versus_{abscissa_variable}.html",
        )
