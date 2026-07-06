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

"""Global VIMSEO configuration."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from vimseo.config.base_configuration_factory import BaseConfigurationFactory
from vimseo.config.configuration_settings import VimseoSettings

LOGGER = logging.getLogger(__name__)


# Detect plugins to agregate the config from plugins with the vimseo config
# Temporary done with try.except of plugin imports,
# until done better with entry points:
def to_snake_case(camel_case: str) -> str:
    """Convert a CamelCase name to snake_case name."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# Plugin config:


plugin_names = BaseConfigurationFactory().class_names
plugin_names.remove("BaseConfiguration")
plugin_names.remove("VimseoSettings")
if len(plugin_names) > 0:
    LOGGER.info(f"Detected plugins: {plugin_names}")

plugin_settings = {}
plugin_config_classes = [VimseoSettings]

for name in plugin_names:
    plugin_config_classes.append(BaseConfigurationFactory().get_class(name))
    local_path = Path.cwd() / f"{name}.yml"
    print(f"Extend config for plugin {to_snake_case(name).split('_settings')[0]}.")
    print(f"Config file looked for is: {local_path}.")
    if local_path.is_file():
        print(f"Config file for plugin {name} found.")
        with Path(local_path).open(encoding="utf-8") as f:
            try:
                plugin_settings.update(yaml.safe_load(f))
            except yaml.YAMLError as exc:
                print(exc)
    else:
        print(
            f"No user config file found for plugin {name}: default settings are loaded."
        )

_configuration = type("AllSettings", tuple(plugin_config_classes[::-1]), {})(
    **plugin_settings
)
"""The global VIMSEO configuration.

The feature is described
on the page [TODO] of the documentation.
"""
