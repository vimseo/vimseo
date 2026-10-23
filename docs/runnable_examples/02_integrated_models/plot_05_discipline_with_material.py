# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This work is licensed under a BSD 0-Clause License.
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
# FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Wrap a GEMSEO discipline with a material
========================================

A GEMSEO discipline becomes a VIMSEO model by deriving a class from
``BaseDisciplineModel``. A material gives the default values of the discipline inputs
named after its properties, and its stochastic properties define an uncertain space.
"""

# %%
from __future__ import annotations

from typing import ClassVar

from gemseo.core.discipline import Discipline
from numpy import atleast_1d
from numpy import linspace
from numpy import where

from vimseo import EXAMPLE_RUNS_DIR
from vimseo.core.base_discipline_model import BaseDisciplineModel
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.material.material import Material
from vimseo.material.material_property import MaterialProperty
from vimseo.material.material_relation import MaterialRelation
from vimseo.utilities.distribution import DistributionParameters

# %%
# The GEMSEO discipline
# ---------------------
#
# A tensile test of a coupon with a bilinear elasto-plastic behaviour. The discipline
# is the one of the user: VIMSEO does not require to modify it.


class TensileCoupon(Discipline):
    """A tensile coupon with a bilinear elasto-plastic behaviour."""

    def __init__(self) -> None:
        super().__init__()
        default_input_data = {
            "width": atleast_1d(25.0),
            "thickness": atleast_1d(2.0),
            "young_modulus": atleast_1d(70000.0),
            "yield_stress": atleast_1d(300.0),
            "tangent_modulus": atleast_1d(1000.0),
            "max_strain": atleast_1d(0.05),
        }
        self.input_grammar.update_from_data(default_input_data)
        self.default_input_data = default_input_data
        self.output_grammar.update_from_data({
            "max_force": atleast_1d(0.0),
            "strain_history": linspace(0.0, 1.0, 3),
            "stress_history": linspace(0.0, 1.0, 3),
        })

    def _run(self, input_data):
        e = input_data["young_modulus"][0]
        yield_stress = input_data["yield_stress"][0]
        strain = linspace(0.0, input_data["max_strain"][0], 50)
        stress = where(
            strain <= yield_stress / e,
            e * strain,
            yield_stress
            + input_data["tangent_modulus"][0] * (strain - yield_stress / e),
        )
        section = input_data["width"][0] * input_data["thickness"][0]
        return {
            "max_force": atleast_1d(stress.max() * section),
            "strain_history": strain,
            "stress_history": stress,
        }


# %%
# The material
# ------------
#
# Its property names are input names of the discipline. The Young modulus and the
# yield stress are stochastic, the tangent modulus is deterministic. A material is
# usually read from a JSON file (``Material.from_json``).

material = Material(
    name="Aluminium",
    material_relations=[
        MaterialRelation(
            name="ElastoPlastic",
            properties=[
                MaterialProperty(
                    name="young_modulus",
                    value=72000.0,
                    lower_bound=60000.0,
                    upper_bound=80000.0,
                    distribution=DistributionParameters(
                        name="Normal", mu=72000.0, sigma=2000.0
                    ),
                ),
                MaterialProperty(
                    name="yield_stress",
                    value=320.0,
                    lower_bound=250.0,
                    upper_bound=400.0,
                    distribution=DistributionParameters(
                        name="Normal", mu=320.0, sigma=15.0
                    ),
                ),
                MaterialProperty(name="tangent_modulus", value=1200.0),
            ],
        )
    ],
)

# %%
# The VIMSEO model
# ----------------
#
# The discipline is set as the ``_DISCIPLINE`` class attribute. A material can be
# declared with the ``MATERIAL_FILE`` class attribute (the path to a material JSON
# file); here it is passed to the constructor, which overrides ``MATERIAL_FILE``.
# The cache of the discipline is disabled: the model manages the cache.


class TensileCouponModel(BaseDisciplineModel):
    """The VIMSEO model of the tensile coupon."""

    _DISCIPLINE = TensileCoupon()
    _EXPECTED_LOAD_CASE = "Dummy"
    PLOTS: ClassVar = [("strain_history", "stress_history")]


model_settings = IntegratedModelSettings(
    directory_archive_root=EXAMPLE_RUNS_DIR / "archive/discipline_with_material",
    directory_scratch_root=EXAMPLE_RUNS_DIR / "scratch/discipline_with_material",
    cache_file_path=EXAMPLE_RUNS_DIR
    / "caches/discipline_with_material/TensileCouponModel_Dummy_cache.hdf",
)
model = TensileCouponModel(material=material, **model_settings.model_dump())

# %%
# The material values are the default values of the inputs of the same names, which
# are classified as material variables:

print(model.description)

# %%
# The model is executed with these default values:

model.execute()
print(model.get_output_data()["max_force"])

# %%
# The stochastic properties of the material define an uncertain space, e.g. to
# propagate the material variability through the model:

print(model.material.to_parameter_space())

# %%
# The results are visualised with the figures defined in ``PLOTS``:

figures = model.plot_results(show=True)
