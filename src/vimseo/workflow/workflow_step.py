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

"""A wrapping of a ``BaseTool`` in a GEMSEO Discipline to enable running workflows of
tools."""

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

from vimseo.tools.tools_factory import ToolsFactory

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from vimseo.tools.base_settings import BaseSettings

LOGGER = logging.getLogger(__name__)


@dataclass
class Input(metaclass=GoogleDocstringInheritanceMeta):
    name: str = ""
    option_key: str = ""


@dataclass
class Output(metaclass=GoogleDocstringInheritanceMeta):
    name: str = ""
    attr_name: str = ""


def deserialize_pydantic_settings(input_settings: Mapping[str, Any]):
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
                create_pydantic_model(name, value, settings)
            else:
                for name_, value_ in value.items():
                    if isinstance(value_, dict):
                        if "__pydantic_model__" in value_:
                            create_pydantic_model(name_, value_, settings[name])
                        else:
                            for name__, value__ in value_.items():
                                if (
                                    isinstance(value__, dict)
                                    and "__pydantic_model__" in value__
                                ):
                                    create_pydantic_model(
                                        name__,
                                        value__,
                                        settings[name][name_],
                                    )
    return settings


def serialize_pydantic_settings(
    input_settings: BaseSettings, attr_names: Iterable[str] = ()
):
    """Serialize (JSON compatible) a ``BaseSettings`` Pydantic model defining a tool
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


def create_pydantic_model(name, value, tool_settings):
    module, klass_name = value["__pydantic_model__"]
    del value["__pydantic_model__"]
    model = getattr(__import__(module, fromlist=[klass_name]), klass_name)
    tool_settings[name] = model(**value)


class WorkflowStep(Discipline):
    default_grammar_type = "SimplerGrammar"

    _tool_settings: BaseSettings
    """The settings of the tool executed by the step."""

    def __init__(
        self,
        name: str,
        tool_name: str,
        tool_settings: BaseSettings,
        tool_constructor_options: dict | None = None,
        inputs: Iterable[Input] = (),
        outputs: Iterable[Output] = (),
    ):
        super().__init__(name)
        self._tool_name = tool_name
        self._tool_constructor_options = tool_constructor_options or {}
        tool = ToolsFactory().create(tool_name, **self._tool_constructor_options)
        tool.update_options(**tool_settings.model_dump())
        self._tool = tool
        self._inputs = inputs
        self._outputs = outputs
        self._tool_settings = tool_settings

        for i in self._inputs:
            data = self._tool._options[i.option_key]
            if data is None:
                self.input_grammar.update_from_types({i.name: None})
            else:
                self.input_grammar.update_from_data({i.name: data})

        for output in self._outputs:
            output_data = (
                self._tool.result
                if output.attr_name == "result"
                else getattr(self._tool.result, output.attr_name)
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
    def tool(self):
        return self._tool

    @property
    def tool_settings(self) -> BaseSettings:
        return self._tool_settings

    @property
    def serialized_settings(self):
        return {
            "name": self.name,
            "tool_name": self._tool_name,
            "inputs": [asdict(i) for i in self._inputs],
            "outputs": [asdict(output) for output in self._outputs],
            "tool_constructor_options": self._tool_constructor_options,
            "tool_settings": serialize_pydantic_settings(self._tool_settings),
        }

    @classmethod
    def from_serialized_settings(cls, **settings):
        step_settings = {}

        step_settings["name"] = settings["name"]
        step_settings["tool_name"] = settings["tool_name"]
        step_settings["tool_constructor_options"] = settings.get(
            "tool_constructor_options", {}
        )

        tool = ToolsFactory().create(
            settings["tool_name"], **step_settings["tool_constructor_options"]
        )

        if "inputs" in settings:
            step_settings["inputs"] = [
                Input(**options) for options in settings["inputs"]
            ]

        if "outputs" in settings:
            step_settings["outputs"] = [
                Output(**options) for options in settings["outputs"]
            ]

        if tool._SETTINGS:
            step_settings["tool_settings"] = tool._SETTINGS(
                **deserialize_pydantic_settings(settings["tool_settings"])
            )
            tool.update_options(**step_settings["tool_settings"].model_dump())
        else:
            step_settings["tool_settings"] = deserialize_pydantic_settings(
                settings["tool_settings"]
            )
            tool.update_options(**step_settings["tool_settings"])

        return cls(**step_settings)

    def _run(self, input_data):
        if not self._tool._INPUTS:
            if self._inputs:
                LOGGER.warning(
                    f"Some inputs are defined but tool {self._tool_name} takes no inputs."
                )
            self._tool.execute(settings=self._tool_settings)
        else:
            inputs = {}
            for i in self._inputs:
                inputs.update(**{i.option_key: self.get_input_data()[i.name]})
            self._tool.execute(
                inputs=self._tool._INPUTS(**inputs), settings=self._tool_settings
            )
        output_data = {}
        for output in self._outputs:
            if output.attr_name == "result":
                output_data[output.name] = self._tool.result
            else:
                output_data[output.name] = getattr(self._tool.result, output.attr_name)
        self._tool.save_results(prefix=self.name)
        # self.io.update_output_data(output_data)
        return output_data

    # def __str__(self):
    #     msg = MultiLineString()
    #     msg.add(f"Name: {self.name}")
    #     msg.add(f"Tool name: {self.name}")
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
    #     msg.add("Tool settings:")
    #     # msg.add(dumps(self.tool_settings, sort_keys=True, indent=4))
    #     msg.add(str(self.tool_settings))
    #     return str(msg)
