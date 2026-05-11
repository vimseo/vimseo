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

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.base_integrated_model import IntegratedModelSettings
from vimseo.core.components.discipline_wrapper_component import (
    DisciplineWrapperComponent,
)


class ModelComposition(IntegratedModel):
    """A class to create a model composition by relying on a base model and
    adding post-processing components on top of it."""

    def __init__(self, load_case_name: str, **options):
        if "base_model" not in options:
            msg = "A base_model must be provided to create a ModelComposition."
            raise ImportError(msg)

        model = options.pop("base_model")
        post_components = (
            options.pop("post_components") if "post_components" in options else []
        )
        options = IntegratedModelSettings(**options).model_dump()

        self.base_model = model

        # Rely on base model cache
        self.cache = None

        full_load_case_name = (
            f"{model._LOAD_CASE_DOMAIN}_{load_case_name}"
            if model._LOAD_CASE_DOMAIN
            else load_case_name
        )

        super().__init__(
            full_load_case_name,
            [DisciplineWrapperComponent(full_load_case_name, model), *post_components],
            **options,
        )

        self._LOAD_CASE_DOMAIN = model._LOAD_CASE_DOMAIN
        self.CURVES = model.CURVES
