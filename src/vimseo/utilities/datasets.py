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

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import NamedTuple

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from numpy import arange
from numpy import asarray
from numpy import atleast_1d
from numpy import full
from numpy import integer
from numpy import isscalar
from numpy import issubdtype
from numpy import mean
from numpy import ndarray
from numpy import ones
from numpy import vstack
from numpy.ma import array
from pandas import DataFrame
from pandas import MultiIndex
from pandas import testing
from pydantic import BeforeValidator

if TYPE_CHECKING:
    from collections.abc import Iterable

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
    """Compute the GEMSEO Dataset from a DataFrame with a_name{a_group}[a_component]
    convention.

    For vectors, naming convention is a_name{a_group}[0], a_name{a_group}[1], ...
    This naming convention is obtained with ``dataset_to_dataframe()`` with argument
    ``suffix_by_group=True``.

    This is the advanced, lossless counterpart of :func:`dataset_to_dataframe`, meant for
    round-tripping a dataset through a mono-indexed DataFrame. To build a dataset from
    data that does not already follow this convention, use :func:`to_dataset` instead.
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
        if get_component(name) != "0":
            continue
        variable_name = get_variable_name(name)
        group_name = get_group_name(name)
        reordered_unique_names.extend(
            unique_name
            for unique_name in unique_names
            if unique_name.split("__group__")[0] == variable_name
            and unique_name.split("__group__")[1] == group_name
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


def _is_sequence_of_vectors(value: Any) -> bool:
    """Whether ``value`` is a sequence whose entries are themselves vectors.

    Strings are not considered as vectors, so that a variable holding text values is
    treated as a sequence of scalars.

    Args:
        value: The value to inspect.

    Returns:
        Whether the entries of ``value`` are vectors.
    """
    if isinstance(value, ndarray):
        return False

    try:
        entries = list(value)
    except TypeError:
        return False

    return any(isinstance(entry, (ndarray, list, tuple)) for entry in entries)


def _pad_ragged_entries(name: str, value: Any) -> ndarray:
    """Stack vectors of different lengths into a 2D array, padding with ``NaN``.

    This mirrors the convention used when reading vectors of variable length from a csv
    file, where the blank cells are filled with ``NaN``.

    Args:
        name: The name of the variable, used in the error message.
        value: A sequence of vectors.

    Returns:
        The padded data, shaped as ``(n_entries, n_components)``.

    Raises:
        ValueError: If an entry cannot be interpreted as a numerical vector.
    """
    try:
        entries = [atleast_1d(asarray(entry, dtype=float)) for entry in value]
    except (TypeError, ValueError) as err:
        msg = (
            f"The variable {name!r} holds vectors of different lengths, "
            "which are only supported for numerical data."
        )
        raise ValueError(msg) from err

    n_components = max(entry.size for entry in entries)
    padded = full((len(entries), n_components), float("nan"))
    for entry_id, entry in enumerate(entries):
        padded[entry_id, : entry.size] = entry
    return padded


def _normalize_variable_data(name: str, value: Any) -> ndarray | None:
    """Normalize the data of a variable to an array shaped ``(n_entries, n_components)``.

    Args:
        name: The name of the variable.
        value: The data of the variable, either a scalar, a vector, an array shaped as
            ``(n_entries, n_components)`` or a sequence of vectors of possibly different
            lengths.

    Returns:
        The normalized data, or ``None`` if ``value`` is a scalar, whose number of
        entries can only be deduced from the other variables.

    Raises:
        ValueError: If the data has more than two dimensions.
    """
    if isinstance(value, ndarray):
        array_value = value
    elif isscalar(value):
        return None
    else:
        try:
            array_value = asarray(value)
        except (TypeError, ValueError):
            return _pad_ragged_entries(name, value)
        if array_value.dtype == object and _is_sequence_of_vectors(value):
            return _pad_ragged_entries(name, value)

    if array_value.ndim == 0:
        return None

    if array_value.ndim == 1:
        return array_value.reshape(-1, 1)

    if array_value.ndim == 2:
        return array_value

    msg = (
        f"The variable {name!r} has {array_value.ndim} dimensions; "
        "expected a scalar, a vector or an array shaped as "
        "(n_entries, n_components)."
    )
    raise ValueError(msg)


def _build_dataset(group_names_to_data: Mapping[str, Mapping[str, Any]]) -> IODataset:
    """Build a dataset from data mapping group names to variable names to values.

    Args:
        group_names_to_data: The data, as ``{group_name: {variable_name: values}}``.

    Returns:
        The dataset.

    Raises:
        ValueError: If the variables do not all have the same number of entries.
    """
    normalized: dict[str, dict[str, ndarray | None]] = {}
    n_entries = 0
    reference_name = ""
    for group_name, variables in group_names_to_data.items():
        normalized[group_name] = {}
        for name, value in variables.items():
            data = _normalize_variable_data(name, value)
            normalized[group_name][name] = data
            if data is None:
                continue
            if reference_name and len(data) != n_entries:
                msg = (
                    f"The variable {name!r} has {len(data)} entries "
                    f"whereas {reference_name!r} has {n_entries}; "
                    "all the variables must have the same number of entries."
                )
                raise ValueError(msg)
            n_entries = len(data)
            reference_name = name

    n_entries = n_entries or 1

    dataset = IODataset()
    for group_name, variables in normalized.items():
        for name, data in variables.items():
            if data is None:
                data = full((n_entries, 1), group_names_to_data[group_name][name])
            dataset.add_variable(name, data, group_name=group_name)

    return dataset


def to_dataset(
    data: Dataset | DataFrame | Mapping[str, Any],
    input_names: Iterable[str] = (),
    output_names: Iterable[str] = (),
) -> IODataset:
    """Convert user data to a GEMSEO dataset.

    This is the entry point used by the tools to accept plain Python data, so that the
    GEMSEO :class:`~gemseo.datasets.dataset.Dataset` API does not have to be learnt.
    The accepted forms are:

    - a mapping of variable names to values, e.g. ``{"dx": [1.0, 0.5], "sigma": [3, 4]}``.
      A value can be a scalar, a vector, an array shaped as ``(n_entries, n_components)``
      for a vector variable, or a sequence of vectors of different lengths, which are
      then padded with ``NaN``;
    - a mapping of group names to such mappings, e.g.
      ``{"inputs": {"dx": ...}, "outputs": {"sigma": ...}}``, to state the groups
      explicitly;
    - a mono-indexed :class:`~pandas.DataFrame`, typically read from a csv file;
    - a :class:`~pandas.DataFrame` following the ``a_name{a_group}[a_component]`` column
      convention, see :func:`dataframe_to_dataset`;
    - a :class:`~gemseo.datasets.dataset.Dataset`, returned unchanged.

    Args:
        data: The data to convert.
        input_names: The names of the variables to place in the input group.
            If empty, no variable is placed in the input group.
        output_names: The names of the variables to place in the output group.
            If empty, no variable is placed in the output group.

    Returns:
        The data as an :class:`~gemseo.datasets.io_dataset.IODataset`.

    Raises:
        TypeError: If the type of ``data`` is not supported.
    """
    if isinstance(data, Dataset):
        dataset = data if isinstance(data, IODataset) else IODataset(data)
        if input_names or output_names:
            return resolve_io_groups(
                dataset, input_names=input_names, output_names=output_names
            )
        return dataset

    if isinstance(data, DataFrame):
        if isinstance(data.columns, MultiIndex):
            return to_dataset(
                IODataset.from_dataframe(data),
                input_names=input_names,
                output_names=output_names,
            )
        if any(GROUP_SEPARATORS[0] in str(name) for name in data.columns):
            return to_dataset(
                dataframe_to_dataset(data),
                input_names=input_names,
                output_names=output_names,
            )
        data = {str(name): data[name].to_numpy() for name in data.columns}

    if not isinstance(data, Mapping):
        msg = (
            f"Cannot build a dataset from an object of type {type(data).__name__}; "
            "expected a mapping of variable names to values, a DataFrame or a Dataset."
        )
        raise TypeError(msg)

    if data and all(isinstance(value, Mapping) for value in data.values()):
        return _build_dataset(data)

    dataset = _build_dataset({Dataset.DEFAULT_GROUP: data})
    if input_names or output_names:
        return resolve_io_groups(
            dataset, input_names=input_names, output_names=output_names
        )
    return dataset


def resolve_io_groups(
    dataset: Dataset,
    model: IntegratedModel | None = None,
    input_names: Iterable[str] = (),
    output_names: Iterable[str] = (),
) -> IODataset:
    """Split the default group of a dataset into an input group and an output group.

    A dataset that already declares an input or an output group is returned unchanged,
    so that this function can be called unconditionally by a tool. Otherwise the roles
    are taken from ``input_names`` and ``output_names`` when given, and from the grammars
    of ``model`` otherwise. Variables matching neither role are left in the default
    group, so that data carried along for reference, such as a batch number, is
    preserved.

    Args:
        dataset: The dataset whose groups are to be resolved.
        model: The model providing the variable roles.
            If ``None``, the roles must be given explicitly.
        input_names: The names of the variables to place in the input group.
            If empty, use the input variables of ``model``.
        output_names: The names of the variables to place in the output group.
            If empty, use the output variables of ``model``.

    Returns:
        The dataset with an input group and an output group.

    Raises:
        ValueError: If the roles of the variables cannot be resolved.
    """
    dataset = dataset if isinstance(dataset, IODataset) else IODataset(dataset)

    group_names = set(dataset.group_names)
    if IODataset.INPUT_GROUP in group_names or IODataset.OUTPUT_GROUP in group_names:
        return dataset

    if Dataset.DEFAULT_GROUP not in group_names:
        return dataset

    available_names = dataset.get_variable_names(Dataset.DEFAULT_GROUP)

    if not input_names and model is not None:
        input_names = model.input_grammar.names

    if not output_names and model is not None:
        output_names = model.get_output_data_names(remove_metadata=True)

    names_to_group_names = {
        name: IODataset.INPUT_GROUP for name in input_names if name in available_names
    }
    names_to_group_names.update({
        name: IODataset.OUTPUT_GROUP for name in output_names if name in available_names
    })

    if not names_to_group_names:
        msg = (
            "Cannot tell the inputs from the outputs of the data. "
            "Either pass a model, name the variables with the ``input_names`` and "
            "``output_names`` settings, or group the data explicitly as "
            f"{{{IODataset.INPUT_GROUP!r}: ..., {IODataset.OUTPUT_GROUP!r}: ...}}. "
            f"The available variables are {available_names}."
        )
        raise ValueError(msg)

    dataset.columns = MultiIndex.from_tuples(
        [
            (
                names_to_group_names.get(variable_name, group_name),
                variable_name,
                component,
            )
            for group_name, variable_name, component in dataset.columns
        ],
        names=dataset.columns.names,
    )
    return dataset


def _coerce_to_dataset(data: Any) -> Any:
    """Convert user data to a dataset, letting ``None`` and unsupported types through.

    Unsupported types are passed on unchanged so that Pydantic reports them, rather than
    this function raising on a value that a field may legitimately accept.

    Args:
        data: The data to convert.

    Returns:
        The data as an :class:`~gemseo.datasets.io_dataset.IODataset` when it can be
        converted, and unchanged otherwise.
    """
    if data is None or isinstance(data, IODataset):
        return data

    if isinstance(data, (Dataset, DataFrame, Mapping)):
        return to_dataset(data)

    return data


DatasetInput = Annotated[IODataset, BeforeValidator(_coerce_to_dataset)]
"""A dataset field accepting a mapping, a DataFrame or a Dataset.

Use this instead of ``Dataset`` or ``IODataset`` when declaring the field of a tool, so
that users can pass the data they already have. The conversion is carried by the
annotation rather than by the tool, so that it also applies when the inputs model is
built directly, as done by the workflow engine.
"""


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
