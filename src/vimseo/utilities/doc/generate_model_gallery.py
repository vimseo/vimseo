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

"""Utilities to automatically add to the documentation gallery a presentation of each
model, with its load cases."""

from __future__ import annotations

import logging
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment
from jinja2 import FileSystemLoader

from vimseo.api import create_model
from vimseo.api import get_available_load_cases
from vimseo.api import get_available_models

if TYPE_CHECKING:
    from collections.abc import Iterable

LOGGER = logging.getLogger(__name__)

EXCLUDED_MODELS = []


def generate_model_examples(
    pkg_name: str, gallery_example_path: str | Path, excluded_models: Iterable[str] = ()
):
    """Generate how_to for each model and load case.

    Based on a template, generate one example in the documentation per model and load
    case, to provide an overview of each.
    """
    vims_root = Path(pkgutil.get_loader("vimseo").get_filename()).parent
    pkg_root = Path(pkgutil.get_loader(pkg_name).get_filename()).parent

    model_names = [
        model_name
        for model_name in get_available_models()
        if model_name not in excluded_models
    ]
    for model_name in model_names:
        for load_case in get_available_load_cases(model_name):
            filename = (
                pkg_root / gallery_example_path / f"plot_{model_name}_{load_case}.py"
            )

            environment = Environment(
                loader=FileSystemLoader(str(vims_root / "utilities/doc/templates/"))
            )
            template = environment.get_template("plot_model.txt")

            model = create_model(model_name, load_case)
            LOGGER.info(f"Created {model_name} with load case {load_case}")
            figure_keys = [
                f"{curve[1]}_vs_{curve[0]}"
                for curve in model.CURVES + model.load_case.plot_parameters.curves
            ]

            content = template.render(
                model_name=model_name,
                load_case=load_case,
                model_summary=model.description.summary,
                figure_keys=figure_keys,
            )
            Path(filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    # To be executed from here.
    generate_model_examples(
        "vimseo", Path.cwd() / "docs/runnable_examples/01_models", EXCLUDED_MODELS
    )
