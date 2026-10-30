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

"""A wrapping of a ``BaseAnalysisNode`` in a GEMSEO Discipline to enable running workflows of
analysis nodes."""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import asdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from docstring_inheritance import GoogleDocstringInheritanceMeta
from gemseo.core.discipline.discipline import Discipline
from pydantic import BaseModel

from vimseo.analysis_nodes.analysis_nodes_factory import AnalysisNodesFactory

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from vimseo.analysis_nodes.base_settings import BaseSettings

LOGGER = logging.getLogger(__name__)


@dataclass
class Input(metaclass=GoogleDocstringInheritanceMeta):
    name: str = ""
    option_key: str = ""


@dataclass
class Output(metaclass=GoogleDocstringInheritanceMeta):
    name: str = ""
    attr_name: str = ""


def _deserialize_pydantic_settings(input_settings: Mapping[str, Any]):
    """Reconstruct the fields of a ``BaseSettings`` as Pydantic model instance if they
    are of this type.

    Only the case of nested Pydantic model fields in dictionaries is handled:

    ```
    class MySettings(BaseSettings):
        pydantic_field: MyPydanticField = MyPydanticField
        nested_pydantic_field: Mapping[str, MyPydanticField] = {}
        double_nested_pydantic_field: Mapping[str, Mapping[str, MyPydanticField]] = {}
    ```

    The case of lists of Pydantic fields is not handled.
    """
    settings = deepcopy(input_settings)
    for name, value in settings.items():
        if isinstance(value, dict):
            if "__pydantic_model__" in value:
                _create_pydantic_model(name, value, settings)
            else:
                for name_, value_ in value.items():
                    if isinstance(value_, dict):
                        if "__pydantic_model__" in value_:
                            _create_pydantic_model(name_, value_, settings[name])
                        else:
                            for name__, value__ in value_.items():
                                if (
                                    isinstance(value__, dict)
                                    and "__pydantic_model__" in value__
                                ):
                                    _create_pydantic_model(
                                        name__,
                                        value__,
                                        settings[name][name_],
                                    )
    return settings


def _serialize_pydantic_settings(
    input_settings: BaseSettings, attr_names: Iterable[str] = ()
):
    """Serialize (JSON compatible) a ``BaseSettings`` Pydantic model defining an analysis node
    settings.

    It handles the case where a field of ``BaseSettings`` is a Pydantic model.
    This field is serialized as a dictionary obtained with ``my_field.model_dump()``,
    and the item {'__pydantic_model__': ``field_module.field_class_name``} is added to
    this dictionary.
    It allows to be able to reconstruct the field as a Pydantic model instance later.
    """
    settings = {}
    default_settings = input_settings.model_dump()
    attr_names = default_settings.keys() if len(attr_names) == 0 else attr_names
    for attr in attr_names:
        # Handle the case where a settings field is a Pydantic model:
        if isinstance(input_settings.model_fields[attr].default, BaseModel):
            settings[attr] = get_pydantic_model_item(
                input_settings.model_fields[attr].default
            )
            settings[attr].update(
                input_settings.model_fields[attr].default.model_dump()
            )
        else:
            # Otherwise use the settings default value
            settings[attr] = default_settings[attr]
    return settings


def get_pydantic_model_item(model: BaseModel):
    return {
        "__pydantic_model__": (
            model.__module__,
            model.__class__.__name__,
        ),
    }


def _create_pydantic_model(name, value, analysis_node_settings):
    module, klass_name = value["__pydantic_model__"]
    del value["__pydantic_model__"]
    model = getattr(__import__(module, fromlist=[klass_name]), klass_name)
    analysis_node_settings[name] = model(**value)


class WorkflowStep(Discipline):
    default_grammar_type = "SimplerGrammar"

    _analysis_node_settings: BaseSettings
    """The settings of the analysis node executed by the step."""

    def __init__(
        self,
        name: str,
        analysis_node_name: str,
        analysis_node_settings: BaseSettings,
        analysis_node_constructor_options: dict | None = None,
        inputs: Iterable[Input] = (),
        outputs: Iterable[Output] = (),
    ):
        super().__init__(name)
        self._analysis_node_name = analysis_node_name
        self._analysis_node_constructor_options = (
            analysis_node_constructor_options or {}
        )
        analysis_node = AnalysisNodesFactory().create(
            analysis_node_name, **self._analysis_node_constructor_options
        )
        analysis_node.update_options(**analysis_node_settings.model_dump())
        self._analysis_node = analysis_node
        self._inputs = inputs
        self._outputs = outputs
        self._analysis_node_settings = analysis_node_settings

        for i in self._inputs:
            data = self._analysis_node._options[i.option_key]
            if data is None:
                self.input_grammar.update_from_types({i.name: None})
            else:
                self.input_grammar.update_from_data({i.name: data})

        for output in self._outputs:
            output_data = (
                self._analysis_node.result
                if output.attr_name == "result"
                else getattr(self._analysis_node.result, output.attr_name)
            )
            if output_data is None:
                self.output_grammar.update_from_types({output.name: None})
            else:
                self.output_grammar.update_from_data({output.name: output_data})

    @property
    def inputs(self) -> Iterable[Input]:
        return self._inputs

    @property
    def outputs(self) -> Iterable[Output]:
        return self._outputs

    @property
    def analysis_node(self):
        return self._analysis_node

    @property
    def analysis_node_settings(self) -> BaseSettings:
        return self._analysis_node_settings

    @property
    def serialized_settings(self):
        return {
            "name": self.name,
            "analysis_node_name": self._analysis_node_name,
            "inputs": [asdict(i) for i in self._inputs],
            "outputs": [asdict(output) for output in self._outputs],
            "analysis_node_constructor_options": self._analysis_node_constructor_options,
            "analysis_node_settings": _serialize_pydantic_settings(
                self._analysis_node_settings
            ),
        }

    @classmethod
    def from_serialized_settings(cls, **settings):
        step_settings = {}

        step_settings["name"] = settings["name"]
        step_settings["analysis_node_name"] = settings["analysis_node_name"]
        step_settings["analysis_node_constructor_options"] = settings.get(
            "analysis_node_constructor_options", {}
        )

        analysis_node = AnalysisNodesFactory().create(
            settings["analysis_node_name"],
            **step_settings["analysis_node_constructor_options"],
        )

        if "inputs" in settings:
            step_settings["inputs"] = [
                Input(**options) for options in settings["inputs"]
            ]

        if "outputs" in settings:
            step_settings["outputs"] = [
                Output(**options) for options in settings["outputs"]
            ]

        step_settings["analysis_node_settings"] = analysis_node._SETTINGS(
            **_deserialize_pydantic_settings(settings["analysis_node_settings"])
        )
        analysis_node.update_options(
            **step_settings["analysis_node_settings"].model_dump()
        )

        return cls(**step_settings)

    def _run(self, input_data):
        if not self._analysis_node._INPUTS:
            if self._inputs:
                LOGGER.warning(
                    f"Some inputs are defined but analysis node {self._analysis_node_name} takes no inputs."
                )
            self._analysis_node.execute(settings=self._analysis_node_settings)
        else:
            inputs = {}
            for i in self._inputs:
                inputs.update(**{i.option_key: self.get_input_data()[i.name]})
            self._analysis_node.execute(
                inputs=self._analysis_node._INPUTS(**inputs),
                settings=self._analysis_node_settings,
            )
        output_data = {}
        for output in self._outputs:
            if output.attr_name == "result":
                output_data[output.name] = self._analysis_node.result
            else:
                output_data[output.name] = getattr(
                    self._analysis_node.result, output.attr_name
                )
        self._analysis_node.save_results(prefix=self.name)
        # self.io.update_output_data(output_data)
        return output_data

    # def __str__(self):
    #     msg = MultiLineString()
    #     msg.add(f"Name: {self.name}")
    #     msg.add(f"Analysis node name: {self.name}")
    #     msg.add("Inputs:")
    #     for input in self._inputs:
    #         msg.indent()
    #         msg.add(str(input))
    #         msg.dedent()
    #     msg.add("Outputs:")
    #     for output in self._outputs:
    #         msg.indent()
    #         msg.add(str(output))
    #         msg.dedent()
    #     msg.add("Analysis node settings:")
    #     # msg.add(dumps(self.analysis_node_settings, sort_keys=True, indent=4))
    #     msg.add(str(self.analysis_node_settings))
    #     return str(msg)
