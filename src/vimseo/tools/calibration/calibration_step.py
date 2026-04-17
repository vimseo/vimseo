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

import logging
from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.opt.base_optimizer_settings import BaseOptimizerSettings
from gemseo.algos.opt.nlopt.settings.nlopt_cobyla_settings import NLOPT_COBYLA_Settings
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.datasets.dataset import Dataset
from gemseo.datasets.io_dataset import IODataset
from gemseo.post.dataset.bars import BarPlot
from gemseo.utils.directory_creator import DirectoryNamingMethod
from gemseo_calibration.calibrator import CalibrationMetricSettings
from gemseo_calibration.scenario import CalibrationScenario
from numpy import array
from numpy import atleast_1d
from numpy import inf
from numpy import linspace
from numpy import ndarray
from pandas import DataFrame
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError
from sympy import parse_expr

from vimseo.api import create_model
from vimseo.config.global_configuration import _configuration as config
from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.tools.base_analysis_tool import BaseAnalysisTool
from vimseo.tools.base_composite_tool import BaseCompositeTool
from vimseo.tools.base_settings import BaseInputs
from vimseo.tools.base_settings import BaseSettings
from vimseo.tools.calibration.calibration_step_result import CalibrationStepResult
from vimseo.tools.post_tools.calibration_plots import CalibrationCurves
from vimseo.utilities.model_data import MetricVariableType
from vimseo.utilities.model_data import decapsulate_length_one_array

if TYPE_CHECKING:
    from collections.abc import Iterable

    from plotly.graph_objs import Figure

LOGGER = logging.getLogger(__name__)


def eval_expr(expr: str, data: Mapping[str, float]):
    """Evaluate a symbolic expression based on dictionary of variable names to values."""
    return float(
        parse_expr(expr.lower()).evalf(
            subs={name.lower(): value for name, value in data.items() if name in expr}
        )
    )


@dataclass
class MetricVariable:
    name: str
    type: MetricVariableType
    mesh: str = ""


def add_namespace(name: str, prefix: str) -> str:
    """Return the namespaced name following GEMSEO convention."""
    return f"{prefix}:{name}"


def get_name(namespaced_name: str) -> str:
    """Return the name from a namespaced name."""
    return namespaced_name.split(":")[1]


def get_namespace(namespaced_name: str) -> str:
    return namespaced_name.split(":")[0]


class CalibrationStepInputs(BaseInputs):
    reference_data: dict[str, IODataset] = Field(
        default={}, description="A mapping between load cases and reference datasets."
    )
    starting_point: dict[str, ndarray | float | int] = Field(
        default={},
        description="The starting point of the optimization."
        "These variables are used to set the model default inputs "
        "and the design space values.",
    )
    design_space: DesignSpace | ParameterSpace | None = Field(
        default=None,
        description="Update the design space built from the models with this design "
        "space. It can be used to restrain the bounds of the design space.",
    )


class CalibrationStepSettings(BaseSettings):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name_to_models: dict[str, str | IntegratedModel] = Field(
        default={},
        description="The mapping between the load cases "
        "and the corresponding model to be used.",
    )
    control_outputs: (
        Mapping[str, Mapping[str, CalibrationMetricSettings]]
        | Mapping[str, CalibrationMetricSettings]
    ) = {}
    input_names: list[str] = Field(
        default=[],
        description="The names of the inputs to be considered for the calibration."
        "If the samples are repeats of the same calibration point, "
        "this variable must be left to default value and "
        "a dummy input is automatically created to fill the input space.",
    )
    parameter_names: list[str] = Field(
        default=[],
        description="The names of the parameters to be calibrated. If left to default, "
        "design space variables are considered.",
    )
    optimizer_name: str = "NLOPT_COBYLA"
    optimizer_settings: BaseOptimizerSettings = NLOPT_COBYLA_Settings()


class CalibrationStep(BaseAnalysisTool):
    """A calibration step to identify material properties based on a model.

    The best parameters are searched to match model outputs against N experimental data
    for a single load case.
    """

    _INPUTS = CalibrationStepInputs

    _SETTINGS = CalibrationStepSettings

    # _STREAMLIT_SETTINGS = StreamlitCalibrationStepSettings

    def __init__(
        self,
        root_directory: str | Path = config.root_directory,
        directory_naming_method: DirectoryNamingMethod = DirectoryNamingMethod.NUMBERED,
        working_directory: str | Path = config.working_directory,
    ):
        super().__init__(
            root_directory=root_directory,
            directory_naming_method=directory_naming_method,
            working_directory=working_directory,
        )
        self.result = CalibrationStepResult()
        self._calibration = None

    def get_metric_curve_names(
        self,
        metric_variable_names: Iterable[str],
    ) -> list[tuple[str]]:
        """Return the names of ``x`` and ``y`` for each curve contained in
        ``metric_variables``."""
        return [
            (metric_variable.mesh, metric_variable.name)
            for metric_variable in metric_variable_names
            if metric_variable.type == MetricVariableType.CURVE
        ]

    def get_metric_scalar_names(
        self,
        metric_variable_names: Iterable[str],
    ) -> list[tuple[str]]:
        """Return the names of the scalars contained in ``metric_variables``."""
        return [
            metric_variable.name
            for metric_variable in metric_variable_names
            if metric_variable.type == MetricVariableType.SCALAR
        ]

    @BaseCompositeTool.validate
    def execute(
        self,
        inputs: CalibrationStepInputs | None = None,
        settings: CalibrationStepSettings | None = None,
        **options,
    ) -> CalibrationStepResult:

        load_cases = list(options["reference_data"].keys())
        models = [
            (
                deepcopy(options["name_to_models"][load_case])
                if isinstance(options["name_to_models"][load_case], IntegratedModel)
                else create_model(
                    options["name_to_models"][load_case],
                    load_case,
                )
            )
            for load_case in load_cases
        ]

        load_cases = [model.load_case.name for model in models]
        reference_datasets = list(options["reference_data"].values())
        input_names = options["input_names"]
        starting_point = options["starting_point"]
        parameter_names = options["parameter_names"]

        try:
            if not options["control_outputs"]:
                msg = "At least one control output must be specified."
                raise ValueError(msg)
            CalibrationMetricSettings(**next(iter(options["control_outputs"].values())))
            control_outputs = dict.fromkeys(load_cases, options["control_outputs"])
        except ValidationError as err:
            control_outputs = options["control_outputs"]
            if not control_outputs:
                msg = "At least one control output must be specified."
                raise ValueError(msg) from err

        if len(input_names) == 0:
            for model in models:
                model.input_grammar.update_from_data(data={"dummy_": atleast_1d(0.0)})
                # TODO see if model grammars could just point to chain grammars
                model._chain.input_grammar.update_from_data(
                    data={"dummy_": atleast_1d(0.0)}
                )
            for reference_data in reference_datasets:
                if "dummy_" not in reference_data.get_variable_names(
                    IODataset.INPUT_GROUP
                ):
                    reference_data.add_variable(
                        "dummy_", atleast_1d(0.0), IODataset.INPUT_GROUP
                    )
            input_names = ["dummy_"]

        specified_design_space = (
            options["design_space"].to_design_space()
            if isinstance(options["design_space"], ParameterSpace)
            else options["design_space"]
        )
        if len(parameter_names) == 0 and specified_design_space is not None:
            parameter_names = specified_design_space.variable_names
        if len(parameter_names) == 0:
            msg = (
                "Since Input ``design_space`` is not specified, "
                "Setting ``parameter_names`` should contain at least one item."
            )
            raise ValueError(msg)
        if set(parameter_names).intersection(set(input_names)):
            msg = (
                "Names of parameters to calibrate and ``input_names`` "
                "should be disjoints."
            )
            raise ValueError(msg)
        self.result.metadata.misc["parameter_names"] = parameter_names
        self.result.metadata.misc["load_cases"] = load_cases

        # Add namespace on model inputs, input names, starting points and control outputs
        for model, load_case in zip(models, load_cases, strict=False):
            for name in [
                name
                for name in list(model.input_grammar.keys())
                if name not in parameter_names
            ]:
                model.add_namespace_to_input(name, load_case)

            for name in model.get_output_data_names():
                model.add_namespace_to_output(name, load_case)

        namespaced_input_names = [
            add_namespace(name, load_case)
            for name in input_names
            for load_case in load_cases
        ]

        for i, load_case in enumerate(load_cases):
            variable_names = reference_datasets[i].variable_names
            reference_datasets[i] = reference_datasets[i].rename(
                {name: add_namespace(name, load_case) for name in variable_names},
                axis=1,
                level=1,
            )

        # Duplicate control outputs by prefixing by namespace
        namespaced_control_outputs = {}
        for load_case, control_outputs_ in control_outputs.items():
            for name, metric_settings in control_outputs_.items():
                key = add_namespace(name, load_case)
                namespaced_control_outputs[key] = deepcopy(control_outputs_[name])
                if metric_settings["mesh"] not in [None, ""]:
                    namespaced_control_outputs[key]["mesh"] = add_namespace(
                        metric_settings["mesh"], load_case
                    )
                    setting_names = list(metric_settings.keys())
                    setting_names.remove("mesh")
                    for name in setting_names:
                        namespaced_control_outputs[key][name] = metric_settings[name]

        reference_data_dict = reference_datasets[0].to_dict_of_arrays(False)
        for reference_data in reference_datasets[1:]:
            reference_data_dict.update(reference_data.to_dict_of_arrays(False))

        # Set default inputs of model, useful if the prior parameters contain variables
        # that are not in the design space.
        for model, load_case in zip(models, load_cases, strict=False):
            model.default_input_data.update({
                add_namespace(name, load_case): atleast_1d(value)
                for name, value in starting_point.items()
                if add_namespace(name, load_case) in model.default_input_data
            })

        design_space = DesignSpace()
        for name in parameter_names:
            default_input_value = None
            if name in starting_point:
                default_input_value = starting_point[name]
            else:
                default_input_values = []
                for model, load_case in zip(models, load_cases, strict=False):
                    namespaced_name = (
                        name
                        if name in parameter_names
                        else add_namespace(name, load_case)
                    )
                    if namespaced_name in model.default_input_data:
                        default_input_values.append(
                            model.default_input_data[namespaced_name]
                        )
                if len(default_input_values) > 0:
                    if default_input_values.count(default_input_values[0]) != len(
                        default_input_values
                    ):
                        msg = (
                            f"Initial value of the design space for variable {name} "
                            "is defined from model default input data. "
                            "However, this value is ambiguous because all models "
                            "do not have the same default value for this variable."
                        )
                        raise ValueError(msg)
                    default_input_value = default_input_values[0]
                if not default_input_value:
                    msg = (
                        f"No initial value was found for variable {name}, "
                        "either in the starting_point or the model default inputs."
                    )
                    raise ValueError(msg)

            if specified_design_space and name in specified_design_space.variable_names:
                design_space.add_variable(
                    name,
                    value=specified_design_space.get_current_value([name]),
                    lower_bound=specified_design_space.get_lower_bound(name),
                    upper_bound=specified_design_space.get_upper_bound(name),
                )
            else:
                design_space.add_variable(
                    name,
                    value=atleast_1d(default_input_value),
                    lower_bound=(
                        model.lower_bounds[name]
                        if name
                        in [name for model in models for name in model.lower_bounds]
                        else -inf
                    ),
                    upper_bound=(
                        model.upper_bounds[name]
                        if name
                        in [name for model in models for name in model.upper_bounds]
                        else inf
                    ),
                )

        self.result.metadata.misc["models"] = {
            model.load_case.name: model.description for model in models
        }
        self.result.metadata.misc["design_space"] = str(design_space)
        LOGGER.info(
            f"Calibration design space: {self.result.metadata.misc['design_space']}"
        )

        calibration_metrics = []
        for variable_name, settings in namespaced_control_outputs.items():
            settings["output"] = variable_name
            calibration_metrics.append(CalibrationMetricSettings(**settings))
        calibration = CalibrationScenario(
            models, namespaced_input_names, calibration_metrics, design_space
        )
        calibration.set_differentiation_method("finite_differences")

        calibration.execute(
            algo_name=options["optimizer_name"],
            reference_data=reference_data_dict,
            **options["optimizer_settings"],
        )

        LOGGER.info(f"Parameters before calibration: {calibration.prior_parameters}")
        LOGGER.info(
            f"Parameters after calibration: "
            f"{decapsulate_length_one_array(calibration.posterior_parameters)}"
        )

        self._metric_variables = []
        for variable_name, settings in namespaced_control_outputs.items():
            if settings["mesh"] not in [None, ""]:
                self._metric_variables.append(
                    MetricVariable(
                        variable_name,
                        MetricVariableType.CURVE,
                        settings["mesh"],
                    )
                )
            elif settings["mesh"] == "":
                self._metric_variables.append(
                    MetricVariable(
                        variable_name,
                        MetricVariableType.CURVE,
                        add_namespace("dummy_", get_namespace(variable_name)),
                    )
                )
            elif reference_data_dict[variable_name].shape[1] > 1:
                self._metric_variables.append(
                    MetricVariable(
                        variable_name,
                        MetricVariableType.VECTOR,
                    )
                )
            else:
                self._metric_variables.append(
                    MetricVariable(
                        variable_name,
                        MetricVariableType.SCALAR,
                    )
                )

        self.result.curve_data.reference_dataframes = defaultdict(list)
        self.result.curve_data.posterior_dataframes = defaultdict(list)
        self.result.curve_data.prior_dataframes = defaultdict(list)
        for result_dataframes, calibration_data in zip(
            [
                self.result.curve_data.reference_dataframes,
                self.result.curve_data.posterior_dataframes,
                self.result.curve_data.prior_dataframes,
            ],
            [
                reference_data_dict,
                calibration.posterior_model_data,
                calibration.prior_model_data,
            ],
            strict=False,
        ):
            for load_case, reference_data in options["reference_data"].items():
                for i in range(len(reference_data)):
                    result_dataframes[load_case].append({})
                    for mesh_name, name in self.get_metric_curve_names(
                        self._metric_variables
                    ):
                        if get_namespace(name) == load_case:
                            variable_names = [name]
                            if get_name(mesh_name) != "dummy_":
                                variable_names.append(mesh_name)
                            data_ = {
                                get_name(name): calibration_data[name][i]
                                for name in variable_names
                            }
                            if get_name(mesh_name) == "dummy_":
                                data_.update({
                                    get_name(mesh_name): linspace(
                                        0.0,
                                        1.0,
                                        len(calibration_data[name][0]),
                                    )
                                })
                            result_dataframes[load_case][i][get_name(name)] = (
                                pd.DataFrame.from_dict(data_)
                            )

        self.result.metadata.misc["name"] = "calibration_step"
        for model, load_case in zip(models, load_cases, strict=False):
            self.result.metadata.misc["name"] += f"_{model.name}-{load_case}"
        self.result.metric_variables = self._metric_variables
        self.result.posterior_parameters = starting_point
        self.result.posterior_parameters.update(calibration.posterior_parameters)
        self.result.posterior_parameters = decapsulate_length_one_array(
            self.result.posterior_parameters
        )
        self.result.prior_parameters = decapsulate_length_one_array(
            calibration.prior_parameters
        )
        self.result.design_space = design_space
        self.result.reference_data = reference_data_dict
        self.result.prior_model_data = calibration.prior_model_data
        self.result.posterior_model_data = calibration.posterior_model_data
        self.result.objective = (
            calibration.formulation.optimization_problem.objective.name
        )

        self.result.post_processing_figures = {}
        self.result.post_processing_figures.update({
            f"optimization_history_{fig_name}": fig
            for fig_name, fig in calibration.post_process(
                "OptHistoryView",
                save=True,
                show=False,
                directory_path=self.working_directory,
            ).figures.items()
        })
        # TODO to be kept?
        for load_case, control_outputs_ in control_outputs.items():
            self.result.post_processing_figures[load_case] = {}
            for output_name in control_outputs_:
                key = f"simulated_versus_reference_{output_name}"
                self.result.post_processing_figures[load_case].update({
                    key: next(
                        iter(
                            calibration.post_process(
                                "DataVersusModel",
                                output=f"{load_case}:{output_name}",
                                save=True,
                                show=False,
                                directory_path=self.working_directory,
                                file_name=f"{key}_load_case_{load_case}.png",
                            ).figures.values()
                        )
                    )
                })

    def plot_results(
        self,
        result: CalibrationStepResult,
        directory_path: str | Path = "",
        save=False,
        show=True,
        font_size: int = 12,
    ) -> Mapping[str, Figure]:

        figures = defaultdict(dict)
        working_directory = (
            self.working_directory if directory_path == "" else Path(directory_path)
        )

        for namespaced_name in self.get_metric_scalar_names(result.metric_variables):
            load_case = get_namespace(namespaced_name)
            name = get_name(namespaced_name)
            category = ["prior", "posterior", "reference"]
            df = DataFrame.from_dict({
                category: array(data_source[namespaced_name]).flatten()
                for category, data_source in zip(
                    category,
                    [
                        result.prior_model_data,
                        result.posterior_model_data,
                        result.reference_data,
                    ],
                    strict=False,
                )
            })
            df = df.T
            df.columns = [str(c) for c in df.columns]
            plot = BarPlot(Dataset.from_dataframe(df))
            plot.title = (
                f"Simulated versus reference for output {name} "
                f"and load case {load_case}"
            )
            plot.font_size = font_size
            plot.labels = category
            figures[load_case].update({
                f"simulated_versus_reference_{name}_bars": plot.execute(
                    save=True,
                    show=False,
                    file_format="html",
                    directory_path=working_directory,
                    file_name=f"simulated_versus_reference_{name}_load_case_{load_case}_bars",
                )[0]
            })

        plot = CalibrationCurves(working_directory=working_directory)
        for abscissa_name, namespaced_name in self.get_metric_curve_names(
            result.metric_variables
        ):
            load_case = get_namespace(namespaced_name)
            name = get_name(namespaced_name)
            plot.execute(
                result.curve_data.posterior_dataframes[load_case],
                result.curve_data.prior_dataframes[load_case],
                result.curve_data.reference_dataframes[load_case],
                get_name(abscissa_name),
                name,
                load_case=load_case,
                font_size=font_size,
                show=show,
                save=save,
            )

            figures[load_case].update({
                f"simulated_versus_reference_curve_{name}_versus_{get_name(abscissa_name)}": plot.result.figure
            })

        return figures
