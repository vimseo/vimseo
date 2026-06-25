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

from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import arange
from numpy import asarray
from numpy import atleast_1d
from numpy import integer
from numpy import issubdtype
from numpy import mean
from numpy import ndarray
from numpy import ones
from numpy import vstack
from numpy.ma import array
from pandas import DataFrame
from pandas import testing

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from vimseo.core.base_integrated_model import IntegratedModel
    from vimseo.tools.post_tools.plot_result import PlotResult
    from vimseo.utilities.distribution import DistributionParameters

SEP = ";"


class Variable(NamedTuple):
    """A convenient data class to define a variable to be placed in a Dataset."""

    name: str
    order_of_magnitude: float
    cov: float = 0.1
    size: int = 1
    is_constant_value: bool = True


def generate_dataset(
    group_names_to_vars: Mapping[str, Iterable[Variable]], nb_samples: int
):
    mock_reference_data = Dataset()
    for group_name, variables in group_names_to_vars.items():
        data = []
        for v in variables:
            if v.is_constant_value:
                data.append(ones(nb_samples) * v.order_of_magnitude)
            else:
                variation = arange(nb_samples)
                data.append(
                    v.order_of_magnitude * (1 + v.cov * (variation - mean(variation)))
                )
        variable_names = [v.name for v in variables]
        variable_names_to_n_components = {v.name: v.size for v in variables}
        mock_reference_data.add_group(
            group_name=group_name,
            data=vstack(data).T,
            variable_names=variable_names,
            variable_names_to_n_components=variable_names_to_n_components,
        )
    return mock_reference_data


# TODO replace by a CustomDOE.
class DatasetAddFromModel:
    @classmethod
    def add_group(
        cls,
        dataset,
        input_group_name: str,
        input_variable_names: Iterable[str],
        model: IntegratedModel,
        output_group_name: str,
        output_variable_name: str,
        bias: float = 0.0,
    ) -> None:
        """Add group based on the outputs of a model, its inputs being contained in the
        dataset."""
        out = []
        for i in range(dataset.shape[0]):
            input_data = {}
            for name in input_variable_names:
                input_data[name] = dataset.get_view(
                    group_names=input_group_name,
                    variable_names=name,
                ).values[i]
            model.execute(input_data)
            out.append(model.get_output_data()[output_variable_name])
        out = array(out)
        out += bias
        dataset.add_group(
            data=out,
            group_name=output_group_name,
            variable_names=output_variable_name,
        )


class DatasetAddFromStatistics:
    def __init__(self):
        self.space_for_sample_generation = ParameterSpace()

    def add_group(
        self,
        dataset,
        group_name: str,
        variable_names: str,
        distributions: Mapping[str, DistributionParameters],
        nb_samples: int,
    ) -> None:
        """Add group based on statistical parameters using OpenTurns distributions."""
        from vimseo.tools.space.random_variable_interface import (
            add_random_variable_interface,
        )

        for name in variable_names:
            assert name in distributions
            add_random_variable_interface(
                self.space_for_sample_generation,
                name,
                distributions[name],
            )
        samples = self.space_for_sample_generation.compute_samples(n_samples=nb_samples)
        measured_dataset = Dataset.from_array(samples, variable_names=variable_names)
        variable_names_to_n_components = dict.fromkeys(variable_names, 1)
        dataset.add_group(
            group_name=group_name,
            variable_names=variable_names,
            data=vstack([
                measured_dataset.get_view(variable_names=name).values.flatten()
                for name in variable_names
            ]).T,
            variable_names_to_n_components=variable_names_to_n_components,
        )


def list_to_str(lst):
    return "_".join(map(str, lst))


def plot_dataset_element(
    dataset,
    sample_id,
    variables,
    abscissa_variable,
    file_name: str = "",
    group_name: str = "",
) -> PlotResult:
    """Visualize row number ``sample_id`` of a dataset as a line plot.

     Useful if the dataset contains vector elements (1D outputs).

    Args:
         dataset: A dataset containing 1D outputs to visualize.
         sample_id: The id of the row to visualize.
         variables: The variables to be plotted as ordinate.
         abscissa_variable: The abscissa variable.
         file_name: The name of the saved file.
         group_name: The name of the group to which ``variables`` and
             ``abscissa_name`` belong.

     Returns:
         The plot result.
    """
    from vimseo.tools.post_tools.line_plot import Lines

    group_name = Dataset.DEFAULT_GROUP if group_name == "" else group_name
    all_variables = [*variables, abscissa_variable]
    dataset_to_plot = Dataset.from_array(
        vstack([
            dataset[group_name][name].to_numpy()[sample_id] for name in all_variables
        ]).T,
        variable_names=all_variables,
        variable_names_to_n_components=dict.fromkeys(all_variables, 1),
    )
    file_name = (
        f"{list_to_str(variables)}_versus_{abscissa_variable}_"
        f"sample_id_{sample_id}.html"
    )
    plot = Lines()
    plot.execute(
        dataset_to_plot,
        variables,
        abscissa_variable,
        show=True,
        file_format="html",
        file_name=file_name,
    )
    return plot.result


def _to_slice_or_list(obj: Any) -> slice | list[Any]:
    """Convert an object to a ``slice`` or a ``list``.

    Args:
        obj: The object.

    Returns:
        The object as a ``slice`` or a ``list``.
    """
    if isinstance(obj, slice):
        return obj

    if not isinstance(obj, ndarray) and obj != 0 and not obj:
        return slice(None)

    return atleast_1d(obj).tolist()


def get_nb_input_variables(dataset: IODataset):
    """Compute the number of input variables."""
    return len(dataset.get_variable_names(group_name=IODataset.INPUT_GROUP))


def get_scalar_names(dataset: Dataset, group_name: str):
    return [
        name
        for name in dataset.get_variable_names(group_name)
        if len(dataset.get_variable_components(group_name, variable_name=name)) == 1
    ]


GROUP_SEPARATORS = ("{", "}")
COMPONENT_SEPARATORS = ("[", "]")


def dataset_to_dataframe(
    dataset: Dataset,
    variable_names: list[str] = (),
    group_names: list[str] = (),
    suffix_by_group: bool = False,
) -> DataFrame:
    """Extracts variables from a GEMSEO dataset, and store them in a mono-indexed
    DataFrame with variable naming convention a_name[a_group][a_component] ."""
    sep = "__group__"
    group_names = group_names if len(group_names) > 0 else dataset.group_names

    name_and_groups = []
    for group_name in group_names:
        name_and_groups.extend(
            f"{name}{sep}{group_name}"
            for name in dataset.get_variable_names(group_name=group_name)
        )
    group_names = [s.split(sep)[-1] for s in name_and_groups]

    names = [v.split(sep)[0] for v in name_and_groups]
    seen = set()

    if suffix_by_group:
        duplicated_names = names
    else:
        duplicated_names = []
        for x in names:
            if x not in seen:
                seen.add(x)
            else:
                duplicated_names.append(x)

    variable_names = variable_names if len(variable_names) > 0 else names
    final_names = [name for name in variable_names if name not in duplicated_names]

    duplicated_name_and_groups = []
    for name in duplicated_names:
        duplicated_name_and_groups.extend(
            v for v in name_and_groups if v.startswith(name)
        )

    ds = dataset.copy()
    for v in duplicated_name_and_groups:
        splitted_name = v.split(sep)
        name = splitted_name[0]
        group_name = splitted_name[1]
        new_name = f"{name}{GROUP_SEPARATORS[0]}{group_name}{GROUP_SEPARATORS[1]}"
        ds.rename_variable(name, new_name, group_name)
        if name in variable_names:
            final_names.append(new_name)

    view = ds.get_view(group_names=group_names, variable_names=final_names)
    df = view.copy()
    df.columns = view.get_columns(as_tuple=False)
    df_as_dict = df.to_dict()
    return DataFrame.from_dict(df_as_dict)


def dataframe_to_dataset(df: DataFrame) -> Dataset:
    """Compute the GEMSEO Dataset from a DataFrame with a_name[a_group][a_component]
    convention.

    For vectors, naming convention is a_name[a_group][0], a_name[a_group][1], ...
    This naming convention is obtained with ``dataset_to_dataframe()`` with argument
    suffix_by_group=True``.
    """

    def get_group_name(suffixed_name: str) -> str:
        return (suffixed_name.split(GROUP_SEPARATORS[1])[0]).split(GROUP_SEPARATORS[0])[
            1
        ]

    def get_variable_name(suffixed_name: str) -> str:
        return suffixed_name.split(GROUP_SEPARATORS[0])[0]

    def get_component(suffixed_name: str) -> str:
        component_suffix = suffixed_name.split(GROUP_SEPARATORS[1])[1]
        return (
            (component_suffix.split(COMPONENT_SEPARATORS[0])[1]).split(
                COMPONENT_SEPARATORS[1]
            )[0]
            if component_suffix
            else "0"
        )

    unique_names_to_group_names = {}
    for name in df.columns.values:
        variable_name = get_variable_name(name)
        group_name = get_group_name(name)
        component = get_component(name)
        unique_names_to_group_names[
            f"{variable_name}__group__{group_name}__component__{component}"
        ] = group_name

    names_and_groups = [
        unique_name.split("__component__")[0]
        for unique_name in unique_names_to_group_names
    ]
    unique_names_to_n_components = {}
    for name in set(names_and_groups):
        unique_names_to_n_components[name] = names_and_groups.count(name)

    unique_names = list(unique_names_to_n_components.keys())
    unique_names_to_group_names = {
        name.split("__component__")[0]: group_name
        for name, group_name in unique_names_to_group_names.items()
    }

    reordered_unique_names = []
    for name in df.columns.values:
        reordered_unique_names.extend(
            unique_name
            for unique_name in unique_names
            if unique_name.startswith(get_variable_name(name))
            and unique_name.split("__group__")[1].startswith(get_group_name(name))
            and get_component(name) == "0"
        )

    dataset = Dataset.from_array(
        df.to_numpy(),
        variable_names=reordered_unique_names,
        variable_names_to_n_components=unique_names_to_n_components,
        variable_names_to_group_names=unique_names_to_group_names,
    )

    for group_name in dataset.group_names:
        for unique_name in dataset.get_variable_names(group_name=group_name):
            name = unique_name.split("__group__")[0]
            dataset.rename_variable(unique_name, name, group_name)

    return dataset.astype({col: df.dtypes[i] for i, col in enumerate(dataset.columns)})


def decode_vector(vector_as_str: str, separator="_") -> ndarray:
    """Decode a stringified vector.

    Args:
        vector_as_str: A vector as a ``string``, under the form of numerical values
        separated by ``separator``. Square brackets at the beginning
        and the end of the string are allowed
        (typically if the string is obtained from str(NumPy.array)).
        separator: The separator between ply angles.

    Returns:
        A vector_as_str as an array of ``floats``, compatible as a model input.
    """
    vector_as_str = vector_as_str.strip("[]")
    splitted_str = vector_as_str.split(separator)
    splitted_str = [val for val in splitted_str if val != ""]
    return asarray(splitted_str, dtype=float)


def encode_vector(vector_numerical: ndarray | list[float | int]):
    """Encode a vector_as_str.

    Example:
        >>> encode_vector(array([0,90,0])
    Args:
        vector_numerical: [ndarray] A 1D array containing numerical values of plies
        angles.
    Returns:
        vector_as_str_str: [ndarray] An array containing a single string of encoded
        angle values.
    """
    if isinstance(vector_numerical, list):
        vector_numerical = array(vector_numerical)

    if array(vector_numerical).ndim != 1 or len(vector_numerical) == 0:
        msg = "Expecting 1D array but it was given "
        raise ValueError(
            msg,
            array(vector_numerical).ndim,
            vector_numerical,
        )
    if not (
        issubdtype(vector_numerical.dtype, integer)
        or issubdtype(vector_numerical.dtype, float)
    ):
        msg = "vector_as_str to encode is expected to be a numerical array, but not "
        raise TypeError(
            msg,
            vector_numerical,
        )

    # [0, 90.1, 0.0] => [0, 90.1, 0]
    vector_as_str_interm = [int(a) if a == int(a) else a for a in vector_numerical]

    # [0, 90.1, 0] => ["0", "90.1", "0"]
    vector_as_str_interm = asarray(vector_as_str_interm, dtype=str)

    # ["0", "90.1", "0"] => ["0_90.1_0"]
    return "_".join(vector_as_str_interm)


def assert_frame_equal_unordered(df1: DataFrame, df2: DataFrame, **kwargs):
    """Compare two DataFrames regardliess of column and row order."""
    cols = sorted(df1.columns)
    df1 = df1[cols]
    df2 = df2[cols]
    testing.assert_frame_equal(df1, df2, **kwargs)
