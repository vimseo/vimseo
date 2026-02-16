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

from __future__ import annotations

import getpass
import logging
import socket
import subprocess
import sys
from collections import defaultdict
from copy import copy
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from os import getlogin
from pathlib import Path
from re import match
from subprocess import CalledProcessError
from time import time
from typing import TYPE_CHECKING
from typing import ClassVar

import numpy as np
from gemseo.caches.simple_cache import SimpleCache
from gemseo.core.chains.chain import MDOChain
from gemseo.core.discipline.base_discipline import CacheType
from gemseo.core.discipline.discipline import Discipline
from gemseo.core.execution_status import ExecutionStatus
from gemseo.core.grammars.json_grammar import JSONGrammar
from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from matplotlib.image import imread
from matplotlib.pyplot import imshow
from numpy import array
from numpy import asarray
from numpy import inf
from pandas import DataFrame
from strenum import StrEnum

from vimseo.core.gemseo_discipline_wrapper import GemseoDisciplineWrapper
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_description import ModelDescription
from vimseo.core.model_metadata import DEFAULT_METADATA
from vimseo.core.model_metadata import MetaData
from vimseo.core.model_metadata import MetaDataNames
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.material.material import Material
from vimseo.storage_management import NAME_TO_ARCHIVE_CLASS
from vimseo.storage_management.scratch_storage import DirectoryScratch
from vimseo.utilities.json_grammar_utils import load_input_bounds
from vimseo.utilities.plotting_utils import plot_curves

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence

    from gemseo.caches.hdf5_cache import HDF5Cache
    from plotly.graph_objs import Figure

    from vimseo.core.components.external_software_component import BaseComponent
    from vimseo.core.load_case import LoadCase
    from vimseo.storage_management.directory_storage import DirectoryArchive

LOGGER = logging.getLogger(__name__)


class IntegratedModel(GemseoDisciplineWrapper):
    """A :class:`~.IntegratedModel` provides a consistent way to integrate
    mechanical
    models, ensuring that the variables used, the model validity range and a definition
    of how this model is verified are prescribed.

    An ``IntegratedModel`` executes a chain of components, themselves being
    GEMSEO disciplines.

    Model inputs and outputs are validated at each model execution through
    JSON grammars. The JSON files are located next to the model class file, or
    next to a parent class. Aside from the variable types, these grammars also
    describe the range of validity of each variable (when applicable)
    and a description of limitations and units.
    All input data are considered required. So the required field in the input JSON
    grammar files does not need to be filled.

    The curves that are plotted through :meth:`plot_results` are defined in class
    attribute ``CURVES``.

    A model is executed by calling method :meth:`~IntegratedModel.execute`,
    to which can be possibly passed a dictionary to specify inputs.

    Variables that are not passed to this method keep their default value, which are
     defined in the pre-processor class constructor.
    All outputs of the model execution are available through
    :meth:`~.gemseo.core.discipline.MDODiscipline.get_output_data`.
    Model outputs can be plotted with :meth:`~IntegratedModel.plot_results`.
    By default, the model has a cache which avoids re-executing the model if the same
    input data have already been used. Default cache is a hdf file.
    Constructor arguments ``directory_scratch_persistency`` and
    ``directory_archive_persistency``
    allows to control the deletion policy of the job directories.
    If a component executes an external software through a subprocess, errors during the
    subprocess are captured by default and the simulation terminates with outputs filled
    with ``NaNs``. The error code output variable is set to 1.
    If constructor argument ``check_subprocess`` is set to ``True``,
    a blocking exception is raised in case of error during model execution,
    which is useful during the development of a model to get explicit error messages.

    For debugging or profiling activities, it may be useful to deactivate the cache.
    You can do this by running on a model instance: ``model.cache = None``.

    Notes:
        Since an ``IntegratedModel`` extends a
        `GEMSEO <https://gemseo.readthedocs.io/en/stable/index.html>`_
        :class:`~.gemseo.core.discipline.MDODiscipline`, it can be used as |gemseo|
        `discipline <https://gemseo.readthedocs.io/en/6.0.0/examples/api
        /plot_discipline.html#discipline>`_.
        Also, |gemseo| capabilities (MLearning, Optimisation) can be used on the model.

    Examples:
        >>> # Run a model with default values, each execution being stored in a unique
        >>> # directory. The archive and scratch persistency is customized.
        >>> # The manager for archiving the results is set to MLFlow.
        >>> from vimseo.api import create_model
        >>> from vimseo.core.model_settings import IntegratedModelSettings
        >>> model = create_model("BendingTestAnalytical", "Cantilever",
        >>>     model_options=IntegratedModelSettings(
        >>>         directory_archive_root=f"my_model_result",
        >>>         directory_scratch_root=f"my_scratch",
        >>>         directory_scratch_persistency=PersistencyPolicy.DELETE_ALWAYS,
        >>>         directory_archive_persistency=PersistencyPolicy.DELETE_IF_FAULTY,
        >>>         archive_manager="MlflowArchive",
        >>>     ),
        >>> )
        >>> model.execute()
    """

    class InputGroupNames(StrEnum):
        """The names of the input variable groups."""

        GEOMETRICAL_VARS = "geometrical variables"
        NUMERICAL_VARS = "numerical variables"
        BC_VARS = "boundary conditions variables"
        MATERIAL_VARS = "material variables"

    _job_name: str | None
    """The name of the directory of jobs executions."""

    __load_case: LoadCase
    """The load case."""

    _archive_manager: DirectoryArchive
    """Storage system for the archive files."""

    _scratch_manager: DirectoryScratch
    """Storage system for the scratch files."""

    job_description: str = ""
    """Free string description of the job to be executed, to be passed as a metadata
    result."""

    _ERROR_CODE_DEFAULT = -1
    """Default value of error_code."""

    MATERIAL_FILE: ClassVar[Path | str] = ""
    """The path to the json file defining the material values."""

    CURVES: ClassVar[Sequence[tuple[str]]] = []
    """The output data to plot as curves. Define a tuple for each curve. It can be load
    case independent or dependent. Only the first two elements of the list of variables
    are considered.The first variable is the abscissa variable and the second value is
    the ordinate.

    Example:
        >>> CURVES = [('strain_history', 'stress_history')]
    """

    FIELDS_FROM_FILE: ClassVar[Mapping[str, str]] = {}

    SUMMARY: ClassVar[str] = ""
    """A brief description of the model (purpose, range of application, hypothesis,
    limitations, similar models)."""

    NUMERICAL_VARIABLE_NAMES: ClassVar[Sequence[str]] = []
    """The input variable names which are numerical parameters."""

    _MATERIAL_GRAMMAR_FILE: ClassVar[Path | str] = ""
    """The grammar to which the material should comply.

    If argument ``dynamic_material`` of :class:`IntegratedModel` constructor
    is set to ``True``, then the material grammar is dynamically defined from
    the material.
    """

    _LOAD_CASE_DOMAIN = ""
    """The domain to which the load case of this model are associated.

    Specifying a non-empty string means that the loaded load case is
    ``{_LOAD_CASE_DOMAIN}_{load_case_name}`` instead of ``{load_case_name}``.
    """

    auto_detect_grammar_files = False
    default_cache_type = Discipline.CacheType.HDF5
    default_grammar_type = Discipline.GrammarType.JSON

    def __init__(
        self,
        load_case_name: str,
        components: Iterable[BaseComponent],
        **options,
    ):
        options = IntegratedModelSettings(**options).model_dump()
        self.name = self.__class__.__name__
        self.__material = (
            Material.from_json(self.MATERIAL_FILE) if self.MATERIAL_FILE != "" else None
        )
        self.__load_case = LoadCaseFactory().create(
            load_case_name, domain=self._LOAD_CASE_DOMAIN
        )

        if options["cache_file_path"] != "":
            self._cache_file_path = options["cache_file_path"]
            Path(self._cache_file_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self._cache_file_path = f"{self.name}_{self.__load_case.name}_cache.hdf"

        super().__init__(name=self.__class__.__name__)
        self.set_cache(
            cache_type=Discipline.CacheType.HDF5,
            hdf_file_path=self._cache_file_path,
            hdf_node_path="node",
        )

        self._job_name = options["job_name"]

        self._run_time = np.nan

        self._datetime = datetime.today()

        self._chain = MDOChain(components)

        self._scratch_manager = DirectoryScratch(
            root_directory=Path(options["directory_scratch_root"]),
            persistency=options["directory_scratch_persistency"],
            job_name=self._job_name,
            model_name=self.__class__.__name__,
            load_case_name=self.__load_case.name,
        )

        archive_options = {
            "persistency": options["directory_archive_persistency"],
            "model_name": self.name,
            "load_case_name": self.__load_case.name,
            "root_directory": Path(options["directory_archive_root"]),
            "job_name": self._job_name,
            "persistent_file_names": [
                names
                for c in self._chain.disciplines
                for names in c._PERSISTENT_FILE_NAMES
            ],
        }
        self._archive_manager = NAME_TO_ARCHIVE_CLASS[options["archive_manager"]](
            **archive_options
        )

        output_names = self._chain.disciplines[-1].output_grammar.names
        self._chain.output_grammar.restrict_to(output_names)

        self.input_grammar = deepcopy(self._chain.input_grammar)
        self.default_input_data = self._chain.default_input_data
        for name in self.input_grammar.names:
            self.input_grammar.required_names.add(name)

        self.output_grammar = deepcopy(self._chain.disciplines[-1].output_grammar)
        self.output_grammar.update_from_data(DEFAULT_METADATA)
        for name in DEFAULT_METADATA:
            self.output_grammar.required_names.add(name)
        for field_name in self.FIELDS_FROM_FILE:
            self.output_grammar.update_from_data({field_name: ["names"]})
            self.output_grammar.required_names.add(field_name)

        # Set status to DONE, to avoid being locked in FAILED mode.
        self._chain._status = ExecutionStatus.Status.DONE
        for disc in self._chain.disciplines:
            disc._status = ExecutionStatus.Status.DONE

        # Set cache of internal disciplines to None, such that the model cache
        # can be deactivated simply with ``model.cache = None``.
        self._chain.cache = None
        for disc in self._chain.disciplines:
            disc.cache = None

        self._component_with_jacobian = self._chain.disciplines[0]
        # TODO check if integration of jacobian is correct
        self._set_differentiated_names(self._chain.disciplines[0])

        if isinstance(self._chain.disciplines[0].input_grammar, JSONGrammar):
            self.lower_bounds, self.upper_bounds, self.input_space = load_input_bounds(
                self._chain.disciplines[0].input_grammar
            )
        else:
            self.input_space = {}
            self.lower_bounds = {}
            self.upper_bounds = {}
            for name in self._chain.disciplines[0].input_grammar.names:
                self.lower_bounds[name] = [-inf]
                self.upper_bounds[name] = [inf]
                self.input_space[name] = [-inf, inf]

        # Set status to DONE, to avoid being locked in FAILED mode.
        self.execution_status.value = ExecutionStatus.Status.DONE

        # Reset execution time, otherwise the execution is cumulated over all the
        # executions of the model instance.
        self._chain.exec_time = 0.0

    def _set_differentiated_names(self, component_with_jacobian):
        self._differentiated_input_names = (
            component_with_jacobian._differentiated_input_names
        )
        self._differentiated_output_names = (
            component_with_jacobian._differentiated_output_names
        )

    @property
    def description(self):
        """The model description."""
        default_inputs_by_group = {}
        for group_name, group_values in self._classify_variables(
            self.default_input_data
        ).items():
            default_inputs_by_group[group_name] = {
                name: value.tolist() for name, value in group_values.items()
            }
        return ModelDescription(
            self.name,
            self.SUMMARY,
            self.load_case,
            self.get_dataflow(),
            default_inputs_by_group,
            copy(self.curves),
        )

    @property
    def image_path(self) -> Path | None:
        """The fully-qualified path to the image illustrating the model.

        If no image is associated to the model, the path to the image associated with the
        load case is returned.
        """
        try:
            image_paths = self.auto_get_file(".png", [self.__load_case.name])
            if len(image_paths) > 1:
                LOGGER.warning(
                    f"There are more than one image associated with"
                    f" model {self.__class__.__name__}"
                    f" and load case {self.__load_case.name}."
                    f" Only the first one is shown."
                )
            return image_paths[0]
        except FileNotFoundError:
            return self.__load_case.image_path

    def show_image(self) -> None:
        """Show the image illustrating the load case."""
        if self.image_path:
            imshow(asarray(imread(self.image_path)))

    @property
    def numerical_variable_names(self):
        """The input variable names which are numerical parameters."""
        return copy(self.NUMERICAL_VARIABLE_NAMES)

    @property
    def boundary_condition_variable_names(self):
        """The input variable names which are boundary condition parameters."""
        return copy(self.load_case.bc_variable_names)

    @property
    def material_variable_names(self):
        """The input variable names which are material parameters."""
        return (
            list(self.__material.get_values_as_dict().keys()) if self.__material else []
        )

    @property
    def geometrical_variable_names(self):
        """The input variable names which are geometrical parameters."""
        return copy([
            name
            for name in self.input_grammar.names
            if name
            not in (
                self.material_variable_names
                + self.numerical_variable_names
                + self.boundary_condition_variable_names
            )
        ])

    def __str__(self):
        return str(self.description)

    def get_dataflow(self):
        """The inputs and outputs of the components of the model.

        Returns:
             A dictionary mapping component name to its input and output names.
        """

        dataflow = {
            "model_inputs": self.get_input_data_names(),
            "model_outputs": self.get_output_data_names(),
        }

        for component in self._chain.disciplines:
            dataflow[component.name] = {
                "inputs": list(component.input_grammar.names),
                "outputs": list(component.output_grammar.names),
            }

        return dataflow

    def _run(self, input_data):
        start_time = time()

        if self._whether_use_scratch_dir():
            self._scratch_manager.create_job_directory()
            LOGGER.info(
                f"Current root directory of scratch directory is "
                f"{self._scratch_manager.root_directory}."
            )

        self._archive_manager.create_job_directory()
        LOGGER.info(
            f"Current root directory of job directory is "
            f"{self._archive_manager.root_directory}."
        )

        for discipline in self._chain.disciplines:
            discipline._job_directory = self._scratch_manager.job_directory

        output_data = self._chain.execute(input_data)

        end_time = time()
        self._run_time = end_time - start_time

        # Fields
        field_file_names = defaultdict(list)
        if self.scratch_job_directory not in ["", None]:
            for f in self.scratch_job_directory.iterdir():
                for name, field_re in self.FIELDS_FROM_FILE.items():
                    if match(field_re, f.name):
                        field_file_names[name].append(f.name)

        self._archive_manager.add_persistent_file_names([
            file_name
            for file_names in field_file_names.values()
            for file_name in file_names
        ])

        output_data.update({
            name: array([str(file_name) for file_name in field_file_names[name]])
            for name, file_names in field_file_names.items()
        })

        # metadata as additional outputs
        meta_data = self.generate_metadata(output_data)
        output_data.update(asdict(meta_data))

        self._manage_persistency(output_data)

        return output_data

    def _compute_jacobian(
        self,
        input_names: Iterable[str] = (),
        output_names: Iterable[str] = (),
    ) -> None:
        # TODO check if integration of jacobian is correct
        self._init_jacobian(
            input_names=self._differentiated_input_names,
            output_names=self._differentiated_output_names,
        )
        self.jac = self._component_with_jacobian.linearize(
            self.get_input_data(), execute=False
        )

    @property
    def n_cpus(self):
        """The number of CPUs to run this model."""
        return 1

    @staticmethod
    def get_metadata_names():
        return [k.name for k in MetaDataNames]

    def get_output_data_names(self, remove_metadata: bool = False) -> list[str]:
        """

        Args:
            remove_metadata: Whether to remove the metadata from the output data names.

        """
        output_data_names = list(self.output_grammar.names)

        if remove_metadata:
            for name in self.get_metadata_names():
                if name in output_data_names:
                    output_data_names.remove(name)

        return output_data_names

    @property
    def load_case(self) -> LoadCase:
        """The load case."""
        return self.__load_case

    @property
    def material(self) -> Material:
        """The material."""
        return self.__material

    @property
    def curves(self) -> Iterable[tuple[str]]:
        return self.__load_case.plot_parameters.curves + self.CURVES

    def plot_results(
        self,
        directory_path: str | Path = "",
        save: bool = True,
        show: bool = False,
        scalar_names: Iterable[str] = (),
        data: str = "CURVES",
    ) -> Mapping[str, Figure]:
        """Plots the results as curves, from definition of curves in CURVES variable.

        Args:
            directory_path: A path where to save the plots. Default is current working
                directory.
            save: Whether to save the plot.
            show: Whether to show the plot.
            scalar_names: The scalars to plot in a scatter matrix. Show all scalars by default.

        Returns:
        """
        directory_path = Path.cwd() if directory_path == "" else Path(directory_path)
        if not directory_path.exists():
            directory_path.mkdir(parents=True)

        LOGGER.info(f"Saving plots to {directory_path.absolute()}")

        from vimseo.core.model_result import ModelResult

        result = ModelResult.from_data(
            {"inputs": self.get_input_data(), "outputs": self.get_output_data()},
            model=self,
        )
        figures = {}
        if data == "CURVES":
            for variables in self.curves:
                file_name = (
                    f"{self.name}_{self.__load_case.name}_"
                    f"{variables[1]}_vs_{variables[0]}.html"
                )
                figures[f"{variables[1]}_vs_{variables[0]}"] = plot_curves(
                    result.get_curve(variables),
                    directory_path=directory_path,
                    file_name=file_name,
                    save=save,
                    show=show,
                )
                LOGGER.info(
                    f"Plot {file_name} is saved to {Path(directory_path) / file_name}"
                )
        elif data == "SCALARS":
            plot = ScatterMatrix(
                Dataset.from_dataframe(
                    DataFrame.from_dict([
                        result.get_numeric_scalars(
                            variable_names=scalar_names,
                        )
                    ])
                )
            )
            figures["scalars"] = plot.execute(
                directory_path=directory_path,
                file_name="scalars.html",
                save=False,
                show=True,
            )
        else:
            msg = f"Unknown data type {data} for plotting."
            raise ValueError(msg)

        return figures

    def auto_get_file(
        self,
        file_suffix: str,
        load_cases: Iterable[str] = (),
    ) -> Iterable[Path]:
        """Return file paths for files following a naming convention and placed next to
        the model class or its parents, or next to a model load case class. Naming
        convention is {model_class_name}{file_suffix} or
        {model_class_name}_{load_case}{file_suffix}.

        Args:
            file_suffix: The suffix, including the extension, of the file to be searched
                in next to model class or its parents.
            load_cases: an iterable of load cases. If specified, only the files placed
                next to these load case classes are searched.
                Otherwise, all load case classes associated to the model are considered.

        Returns:
            A list of file paths.
        """
        from vimseo.api import get_available_load_cases

        cls = self.__class__
        model_name = cls.__name__
        load_cases = load_cases or get_available_load_cases(model_name)
        classes = [cls] + [
            base for base in cls.__bases__ if issubclass(base, Discipline)
        ]
        names = [model_name] + [cls.__name__ for cls in classes[1:]]

        matching_files = []
        for cls, name in zip(classes, names, strict=False):
            class_module = sys.modules[cls.__module__]
            directory_path = Path(class_module.__file__).parent.absolute()
            file_path = directory_path / f"{name}{file_suffix}"
            if file_path.is_file():
                matching_files.append(file_path)
            for load_case in load_cases:
                file_path = directory_path / f"{name}_{load_case}{file_suffix}"
                if file_path.is_file():
                    matching_files.append(file_path)

        if not matching_files:
            msg = (
                f"No files with suffix {file_suffix} were found next "
                f"to the model {self.name} or its parent class."
            )
            raise FileNotFoundError(msg)

        return matching_files

    @property
    def scratch_job_directory(self) -> Path | str:
        """The Path to the scratch job directory, once the model is executed.

        Before model execution, or if the model uses the cache, the empty string is
        returned.
        """

        return self._scratch_manager.job_directory

    @property
    def run(self) -> BaseComponent:
        """The component running the external software."""
        return self._chain.disciplines[0]

    def _classify_variables(self, data):
        """Split a dictionary of variables according to the variable groups:
         geometrical, material,
         boundary conditions and numerical variables.

        Args:
            data: a dictionary mapping variable names to their value.

        Return:
            ``data`` splitted according to the variable groups.
        """
        return {
            self.InputGroupNames.NUMERICAL_VARS: {
                name: value
                for name, value in data.items()
                if name in self.numerical_variable_names
            },
            self.InputGroupNames.BC_VARS: {
                name: value
                for name, value in data.items()
                if name in self.boundary_condition_variable_names
            },
            self.InputGroupNames.GEOMETRICAL_VARS: {
                name: value
                for name, value in data.items()
                if name in self.geometrical_variable_names
            },
            self.InputGroupNames.MATERIAL_VARS: {
                name: value
                for name, value in data.items()
                if name in self.material_variable_names
            },
        }

    def generate_metadata(self, output_data_raw) -> MetaData:

        if self._chain.execution_status.value != ExecutionStatus.Status.DONE:
            error = 1
        else:
            error = output_data_raw[MetaDataNames.error_code][0]

        here = str(Path(__file__).parent)
        try:
            vims_git_version = (
                subprocess
                .check_output(["git", "-C", here, "rev-parse", "HEAD"])
                .decode("utf-_8")
                .strip()
            )
        except CalledProcessError:
            LOGGER.warning(
                "Model metadata: git is not available, git commit cannot be determined."
            )
            vims_git_version = ""
        if sys.platform.startswith("win"):
            user = getlogin()
        else:
            user = getpass.getuser()
        return MetaData(**{
            MetaDataNames.model: array([self.__class__.__name__]),
            MetaDataNames.load_case: array([self.__load_case.name]),
            MetaDataNames.error_code: array([error]),
            MetaDataNames.description: array([str(self.job_description)]),
            MetaDataNames.job_name: array([self._job_name]),
            # Use a non-empty list in the absence of persistent files, otherwise
            # this variable is not stored in the cache.
            MetaDataNames.persistent_result_files: (
                array([""])
                if len(self._archive_manager.persistent_file_names) == 0
                else array(self._archive_manager.persistent_file_names)
            ),
            MetaDataNames.n_cpus: array([
                self.n_cpus if hasattr(self, "n_cpus") else 0
            ]),
            MetaDataNames.date: array([datetime.today().isoformat(" ")]),
            MetaDataNames.cpu_time: array([self._run_time]),
            MetaDataNames.user: array([user]),
            MetaDataNames.machine: array([str(socket.gethostname())]),
            MetaDataNames.vims_git_version: array([vims_git_version]),
            MetaDataNames.directory_archive_root: array([
                str(self._archive_manager._root_directory.resolve())
            ]),
            MetaDataNames.directory_archive_job: array([
                str(self._archive_manager.job_directory)
            ]),
            MetaDataNames.directory_scratch_root: array([
                str(self._scratch_manager._root_directory.resolve())
            ]),
            MetaDataNames.directory_scratch_job: array([
                str(self._scratch_manager.job_directory)
            ]),
        })

    def create_cache_from_archive(self, run_ids: Iterable[str] = ()) -> HDF5Cache:
        """Defines a temporary HDF5 cache file, based on results found on the current
        archive."""

        # cache file preparation
        cache_dir_path = Path(self._cache_file_path).parent
        self._cache_file_path = Path(
            cache_dir_path
            / f"{self.__class__.__name__}_{self.__load_case.name}_from_archive.hdf"
        )
        self._cache_file_path.unlink(
            missing_ok=True
        )  # delete possible old tmp cache file
        # note that tolerance is important for now: see issue #233.

        self.set_cache(
            cache_type=Discipline.CacheType.HDF5,
            hdf_file_path=self._cache_file_path,
            hdf_node_path="node",
            tolerance=1.0e-10,
        )

        results = self._archive_manager.get_archived_results(run_ids=run_ids)
        if results is None:
            return None

        for result in results:
            if not isinstance(self.cache, SimpleCache):
                to_array = self.output_grammar.data_converter.convert_value_to_array
                for name, value in result["outputs"].items():
                    result["outputs"][name] = to_array(name, value)

            self.cache.cache_outputs(result["inputs"], result["outputs"])
            # jacobian = None
            #
            # # append a cache entry with the current result
            # self.cache[result["inputs"]] = (result["outputs"], jacobian)

        return self.cache

    def _manage_persistency(self, output_data):
        """Write results in archive."""

        # TODO refactor when ModelResult is implemented
        result_model = {"inputs": self.get_input_data(), "outputs": output_data}

        self._archive_manager.enforce_persistency_policy(result_model)

        self._archive_manager.copy_persistent_files(self._scratch_manager.job_directory)

        self._scratch_manager.enforce_persistency_policy(result_model)

    def _whether_use_scratch_dir(self):
        return any(d.USE_JOB_DIRECTORY for d in self._chain.disciplines)

    @property
    def archive_manager(self):
        """The archive manager."""
        return self._archive_manager

    def reset_cache(self, new_cache_path: str | Path):
        """Create a new cache with another file path.

        Has an effect only for ``HDF5`` cache.
        """
        self._cache_file_path = new_cache_path
        self.set_cache(
            cache_type=CacheType.HDF5,
            hdf_file_path=self._cache_file_path,
            hdf_node_path="node",
        )
