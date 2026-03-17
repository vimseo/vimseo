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

import re
from pathlib import Path

import pytest
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.uncertainty.distributions.base_distribution import (
    InterfacedDistributionSettings,
)
from numpy import sign

import vimseo.tools as tools
from vimseo.api import create_model
from vimseo.problems.mock.mock_pre_run_post.mock_main import X1_DEFAULT_VALUE
from vimseo.tools.lib.space_builders import FromCenterAndCov
from vimseo.tools.lib.space_builders import FromMinAndMax
from vimseo.tools.lib.space_builders import FromModelCenterAndCov
from vimseo.tools.lib.space_builders import FromModelMinAndMax
from vimseo.tools.space.random_variable_interface import add_random_variable_interface
from vimseo.tools.space.space_tool import SpaceTool
from vimseo.utilities.distribution import DistributionSettings
from vimseo.utilities.distribution_utils import check_distribution

TOOL_PATH = Path(tools.__path__[0])


@pytest.mark.parametrize(
    ("interface_type", "distribution_name", "settings"),
    [
        (
            "settings_tuple",
            "",
            InterfacedDistributionSettings(name="Normal", parameters=(1.0, 0.05)),
        ),
        (
            "settings_kwargs",
            "OTNormalDistribution",
            DistributionSettings(name="Normal", sigma=0.05, mu=1.0),
        ),
        (
            "settings_kwargs",
            "OTUniformDistribution",
            DistributionSettings(name="Uniform", lower=-1.0, upper=2.0),
        ),
        (
            "settings_kwargs",
            "OTTriangularDistribution",
            DistributionSettings(name="Triangular", lower=-1.0, upper=1.0, mode=0.0),
        ),
        (
            "settings_tuple",
            "OTWeibullDistribution",
            InterfacedDistributionSettings(
                name="WeibullMin", parameters=(1.0, 2.0, 0.0)
            ),
        ),
        (
            "settings_tuple",
            "OTExponentialDistribution",
            InterfacedDistributionSettings(name="Exponential", parameters=(1.0, 0.0)),
        ),
        (
            "settings_kwargs",
            "OTNormalDistribution",
            DistributionSettings(
                name="Normal", sigma=0.05, mu=1.0, lower_bound=0.9, upper_bound=1.1
            ),
        ),
        (
            "settings_kwargs",
            "OTUniformDistribution",
            DistributionSettings(
                name="Uniform", lower=0.0, upper=2.0, lower_bound=0.5, upper_bound=1.5
            ),
        ),
        (
            "settings_kwargs",
            "OTTriangularDistribution",
            DistributionSettings(
                name="Triangular",
                lower=-1.0,
                upper=1.0,
                mode=0.0,
                lower_bound=-0.5,
                upper_bound=0.5,
            ),
        ),
    ],
)
def test_random_variable_interface_with_gemseo(
    tmp_wd, interface_type, distribution_name, settings
):
    """Check the instantiation of a gemseo OT distribution."""
    parameter_space = ParameterSpace()
    add_random_variable_interface(parameter_space, "x1", settings)
    # Put this logic into the check_distribution method
    if interface_type == "settings_tuple":
        check_distribution(
            parameter_space,
            "x1",
            parameters=settings.model_dump()["parameters"],
        )
    else:
        check_distribution(
            parameter_space,
            "x1",
            **settings.model_dump(),
        )


@pytest.mark.parametrize(
    "distribution_name",
    [
        "OTNormalDistribution",
    ],
)
def test_unavailable_distributions(tmp_wd, distribution_name):
    """Check that a space of parameters can be created from minimum and maximum
    values."""
    variable_name = "E"
    space_tool = SpaceTool()
    minimum_values = {variable_name: -1.0}
    maximum_values = {variable_name: 1.0}

    msg = (
        f"Distribution name {distribution_name} must be in "
        f"('OTUniformDistribution', 'OTTriangularDistribution')"
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        space_tool.execute(
            distribution_name=distribution_name,
            space_builder_name="FromMinAndMax",
            minimum_values=minimum_values,
            maximum_values=maximum_values,
        )


ALL_AVAILABLE_DISTRIBUTIONS = (
    "OTUniformDistribution",
    "OTTriangularDistribution",
    "OTNormalDistribution",
)
AVAILABLE_DISTRIBUTIONS_MIN_AND_MAX = (
    "OTUniformDistribution",
    "OTTriangularDistribution",
)


@pytest.mark.parametrize(
    ("space_builder", "expected_available_distribution"),
    [
        (FromCenterAndCov(), ALL_AVAILABLE_DISTRIBUTIONS),
        (FromMinAndMax(), AVAILABLE_DISTRIBUTIONS_MIN_AND_MAX),
        (FromModelCenterAndCov(), ALL_AVAILABLE_DISTRIBUTIONS),
        (FromModelMinAndMax(), AVAILABLE_DISTRIBUTIONS_MIN_AND_MAX),
    ],
)
def test_available_distributions(
    tmp_wd, space_builder, expected_available_distribution
):
    """Check the available distributions of the SpaceBuilder."""
    assert set(space_builder.get_available_distributions()) == set(
        expected_available_distribution
    )


@pytest.mark.parametrize(
    ("distribution_name", "center", "expected_minimum", "expected_maximum"),
    [
        ("OTUniformDistribution", 0.5, 0.475, 0.525),
        ("OTNormalDistribution", 0.5, None, None),
        ("OTTriangularDistribution", 0.5, 0.475, 0.525),
        ("OTTriangularDistribution", -0.5, -0.525, -0.475),
    ],
)
def test_update_from_center_and_cov(
    tmp_wd, distribution_name, center, expected_minimum, expected_maximum
):
    """Check that a space of parameters can be created from center values and a
    coefficient of variation around these values."""
    space_tool = SpaceTool()
    center_values = {"force_relative_location": center}
    cov = 0.05
    space_tool.execute(
        distribution_name=distribution_name,
        space_builder_name="FromCenterAndCov",
        center_values=center_values,
        cov=cov,
    )
    name = "force_relative_location"
    if distribution_name == "OTUniformDistribution":
        check_distribution(
            space_tool.parameter_space,
            name,
            lower=expected_minimum,
            upper=expected_maximum,
            lower_bound=None,
            upper_bound=None,
        )
    elif distribution_name == "OTNormalDistribution":
        check_distribution(
            space_tool.parameter_space,
            name,
            mu=center,
            sigma=abs(cov * center),
            lower_bound=expected_minimum,
            upper_bound=expected_maximum,
        )
    elif distribution_name == "OTTriangularDistribution":
        check_distribution(
            space_tool.parameter_space,
            name,
            mode=center,
            lower=expected_minimum,
            upper=expected_maximum,
        )


@pytest.mark.parametrize(
    ("distribution_name", "center", "lb", "ub"),
    [
        ("OTUniformDistribution", 0.5, None, None),
        ("OTUniformDistribution", 0.5, 0.48, 0.5),
        ("OTTriangularDistribution", 0.5, None, None),
        ("OTTriangularDistribution", 0.5, 0.48, 0.5),
        ("OTNormalDistribution", 0.5, 0.48, 0.5),
    ],
)
def test_update_from_center_and_cov_with_truncation(
    tmp_wd,
    distribution_name,
    center,
    lb,
    ub,
):
    """Check that distributions defined from center values and a coefficient of variation
    are truncated according to specified minimum and maximum values."""
    space_tool = SpaceTool()
    name = "force_relative_location"
    center_values = {name: center}
    lower_bounds = {name: lb} if lb is not None else None
    upper_bounds = {name: ub} if ub is not None else None
    cov = 0.05

    expected_minimum = center * (1 - sign(center) * cov)
    expected_maximum = center * (1 + sign(center) * cov)
    space_tool.execute(
        distribution_name=distribution_name,
        space_builder_name="FromCenterAndCov",
        center_values=center_values,
        cov=cov,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
    )
    if distribution_name == "OTUniformDistribution":
        check_distribution(
            space_tool.parameter_space,
            name,
            lower=expected_minimum,
            upper=expected_maximum,
            lower_bound=lb,
            upper_bound=ub,
        )
    elif distribution_name == "OTNormalDistribution":
        check_distribution(
            space_tool.parameter_space,
            name,
            mu=center,
            sigma=abs(cov * center),
            lower_bound=lb,
            upper_bound=ub,
        )
    elif distribution_name == "OTTriangularDistribution":
        check_distribution(
            space_tool.parameter_space,
            name,
            mode=center,
            lower=expected_minimum,
            upper=expected_maximum,
            lower_bound=lb,
            upper_bound=ub,
        )


@pytest.mark.parametrize(
    (
        "distribution_name",
        "minimum",
        "maximum",
        "center",
        "expected_mode",
        "center_expression",
    ),
    [
        ("OTUniformDistribution", -1.0, 2.0, 0.5, None, ""),
        ("OTTriangularDistribution", -1.0, 2.0, None, 0.5, ""),
        ("OTTriangularDistribution", -1.0, 2.0, None, -1.0, "mini"),
    ],
)
def test_update_from_min_and_max(
    tmp_wd,
    distribution_name,
    minimum,
    maximum,
    center,
    expected_mode,
    center_expression,
):
    """Check that a space of parameters can be created from minimum and maximum
    values."""
    variable_name = "young_modulus"
    space_tool = SpaceTool()
    minimum_values = {variable_name: minimum}
    maximum_values = {variable_name: maximum}
    space_tool.execute(
        distribution_name=distribution_name,
        space_builder_name="FromMinAndMax",
        minimum_values=minimum_values,
        maximum_values=maximum_values,
        center_value_expr=center_expression,
    )
    assert {variable_name} == set(space_tool.parameter_space.variable_names)
    if distribution_name == "OTUniformDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            lower=minimum,
            upper=maximum,
            lower_bound=None,
            upper_bound=None,
        )
    elif distribution_name == "OTTriangularDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mode=expected_mode,
            lower=minimum,
            upper=maximum,
        )


def test_wrong_min_and_max_values(tmp_wd):
    """Check that a space of parameters can be created from minimum and maximum
    values."""
    space_tool = SpaceTool()
    minimum_values = {"young_modulus": -1.0, "relative_dplt_location": -1.0}
    maximum_values = {"relative_dplt_location": -1.0}
    msg = (
        "Variable names for minimum dict_keys(['young_modulus', 'relative_dplt_location']) "
        "and maximum dict_keys(['relative_dplt_location']) must be the same."
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        space_tool.execute(
            distribution_name="OTUniformDistribution",
            space_builder_name="FromMinAndMax",
            minimum_values=minimum_values,
            maximum_values=maximum_values,
        )


# TODO test for use_default_values_as_center = True
@pytest.mark.parametrize(
    ("distribution_name", "use_default_values_as_center", "expected_mode"),
    [
        ("OTUniformDistribution", False, None),
        # model range for x1 is [-1.0, 1.5], so the mid point is 0.25
        ("OTTriangularDistribution", False, 0.25),
        ("OTTriangularDistribution", True, X1_DEFAULT_VALUE),
    ],
)
def test_update_from_model_min_and_max(
    tmp_wd, distribution_name, use_default_values_as_center, expected_mode
):
    """Check that a space of parameters can be created from the minimum and maximum
    bounds of a model."""
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    space_tool = SpaceTool()
    variable_name = "x1"
    space_tool.execute(
        distribution_name=distribution_name,
        space_builder_name="FromModelMinAndMax",
        model=model,
        variable_names=[variable_name],
        use_default_values_as_center=use_default_values_as_center,
    )
    assert {variable_name} == set(space_tool.parameter_space.variable_names)
    expected_minimum = model.lower_bounds[variable_name]
    expected_maximum = model.upper_bounds[variable_name]
    if distribution_name == "OTUniformDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            lower=expected_minimum,
            upper=expected_maximum,
            lower_bound=None,
            upper_bound=None,
        )
    elif distribution_name == "OTTriangularDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mode=expected_mode,
            lower=expected_minimum,
            upper=expected_maximum,
        )


@pytest.mark.parametrize(
    (
        "distribution_name",
        "expected_lb",
        "expected_ub",
        "cov",
        "use_default_values_as_center",
    ),
    [
        ("OTUniformDistribution", None, None, 0.05, True),
        (
            "OTNormalDistribution",
            None,
            None,
            0.05,
            True,
        ),
        ("OTTriangularDistribution", None, None, 0.05, True),
        ("OTTriangularDistribution", None, None, 0.05, False),
        ("OTTriangularDistribution", -1.0, 1.5, 10.0, False),
    ],
)
def test_update_from_model_center_and_cov(
    tmp_wd,
    distribution_name,
    expected_lb,
    expected_ub,
    cov,
    use_default_values_as_center,
):
    """Check that a space of parameters can be created from the default or center values
    of a model and a coefficient of variation around these values."""
    space_tool = SpaceTool()
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    variable_name = "x1"
    space_tool.execute(
        distribution_name=distribution_name,
        space_builder_name="FromModelCenterAndCov",
        model=model,
        variable_names=[variable_name],
        use_default_values_as_center=use_default_values_as_center,
        cov=cov,
        truncate_to_model_bounds=False,
    )
    if use_default_values_as_center:
        center = model.default_input_data[variable_name][0]
    else:
        center = 0.5 * (
            model.lower_bounds[variable_name] + model.upper_bounds[variable_name]
        )
    expected_minimum = center * (1 - sign(center) * cov)
    expected_maximum = center * (1 + sign(center) * cov)

    if distribution_name == "OTUniformDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            lower=expected_minimum,
            upper=expected_maximum,
            lower_bound=None,
            upper_bound=None,
        )
    elif distribution_name == "OTNormalDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mu=center,
            sigma=abs(cov * center),
            lower_bound=None,
            upper_bound=None,
        )
    elif distribution_name == "OTTriangularDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mode=center,
            lower=expected_minimum,
            upper=expected_maximum,
        )


@pytest.mark.parametrize(
    (
        "distribution_name",
        "expected_lb",
        "expected_ub",
        "cov",
        "use_default_values_as_center",
    ),
    [
        ("OTUniformDistribution", None, None, 0.05, True),
        (
            "OTNormalDistribution",
            None,
            None,
            0.05,
            True,
        ),
        ("OTTriangularDistribution", None, None, 0.05, True),
    ],
)
def test_update_vector_from_model_center_and_cov(
    tmp_wd,
    distribution_name,
    expected_lb,
    expected_ub,
    cov,
    use_default_values_as_center,
):
    """Check that a space of parameters can be created from the default or center values
    of a model and a coefficient of variation around these values."""
    space_tool = SpaceTool()
    model = create_model("MockModelPersistent", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    variable_name = "x3"
    space_tool.execute(
        distribution_name=distribution_name,
        space_builder_name="FromModelCenterAndCov",
        model=model,
        variable_names=[variable_name],
        use_default_values_as_center=use_default_values_as_center,
        cov=cov,
        truncate_to_model_bounds=False,
    )
    if use_default_values_as_center:
        center = model.default_input_data[variable_name]
    else:
        center = 0.5 * (
            model.lower_bounds[variable_name] + model.upper_bounds[variable_name]
        )
    expected_minimum = center * (1 - sign(center) * cov)
    expected_maximum = center * (1 + sign(center) * cov)

    if distribution_name == "OTUniformDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            lower=expected_minimum,
            upper=expected_maximum,
            lower_bound=None,
            upper_bound=None,
        )
    elif distribution_name == "OTNormalDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mu=center,
            sigma=abs(cov * center),
            lower_bound=None,
            upper_bound=None,
        )
    elif distribution_name == "OTTriangularDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mode=center,
            lower=expected_minimum,
            upper=expected_maximum,
        )


@pytest.mark.parametrize("cov", [0.05, 100.0])
@pytest.mark.parametrize(
    "distribution_name",
    [
        "OTUniformDistribution",
        "OTTriangularDistribution",
        "OTNormalDistribution",
    ],
)
def test_update_from_model_center_and_cov_with_truncation(
    tmp_wd,
    cov,
    distribution_name,
):
    """Check that a space of parameters can be created from the default or center values
    of a model and a coefficient of variation, and that the distributions are truncated
    according to the model input bounds."""
    space_tool = SpaceTool()
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    variable_name = "x1"
    space_tool.execute(
        distribution_name=distribution_name,
        space_builder_name="FromModelCenterAndCov",
        model=model,
        variable_names=[variable_name],
        use_default_values_as_center=True,
        cov=cov,
        truncate_to_model_bounds=True,
    )
    center = model.default_input_data[variable_name]
    minimum = center * (1 - sign(center) * cov)
    maximum = center * (1 + sign(center) * cov)

    if distribution_name == "OTUniformDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            lower=minimum,
            upper=maximum,
            lower_bound=max(model.lower_bounds[variable_name], minimum),
            upper_bound=min(model.upper_bounds[variable_name], maximum),
        )
    elif distribution_name == "OTNormalDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mu=center,
            sigma=abs(cov * center),
            lower_bound=model.lower_bounds[variable_name],
            upper_bound=model.upper_bounds[variable_name],
        )
    elif distribution_name == "OTTriangularDistribution":
        check_distribution(
            space_tool.parameter_space,
            variable_name,
            mode=center,
            lower=minimum,
            upper=maximum,
            lower_bound=max(model.lower_bounds[variable_name], minimum),
            upper_bound=min(model.upper_bounds[variable_name], maximum),
        )


def test_update_from_non_empty_space(tmp_wd):
    space_tool = SpaceTool()
    model = create_model("MockModel", "LC1")
    model.EXTRA_INPUT_GRAMMAR_CHECK = True
    cov = 0.05
    space_tool.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromModelCenterAndCov",
        variable_names=["x1"],
        model=model,
        use_default_values_as_center=True,
        cov=cov,
        truncate_to_model_bounds=False,
    )
    center = model.default_input_data["x1"][0]
    check_distribution(
        space_tool.parameter_space,
        "x1",
        lower=center * (1 - sign(center) * cov),
        upper=center * (1 + sign(center) * cov),
        mode=center,
    )
    cov = 0.07
    space_tool.execute(
        distribution_name="OTTriangularDistribution",
        space_builder_name="FromModelCenterAndCov",
        variable_names=["x1"],
        model=model,
        use_default_values_as_center=True,
        cov=cov,
    )
    check_distribution(
        space_tool.parameter_space,
        "x1",
        lower=center * (1 - sign(center) * cov),
        upper=center * (1 + sign(center) * cov),
        mode=center,
    )


def test_variable_name_order(tmp_wd):
    """Check that the order of the variables in the parameter space is reproducible."""
    for _i in range(10):
        space_tool = SpaceTool()
        space_tool.execute(
            distribution_name="OTTriangularDistribution",
            space_builder_name="FromMinAndMax",
            minimum_values={
                "length": 200.0,
                "width": 5.0,
                "height": 5.0,
                "imposed_dplt": 0.0,
                "relative_dplt_location": 0.1,
            },
            maximum_values={
                "length": 1000.0,
                "width": 50.0,
                "height": 50.0,
                "imposed_dplt": 20.0,
                "relative_dplt_location": 1.0,
            },
        )
        assert space_tool.parameter_space.variable_names == [
            "length",
            "width",
            "height",
            "imposed_dplt",
            "relative_dplt_location",
        ]


def test_grammar_names(tmp_wd):
    """Check that the property ``grammar_names`` returns the grammar names."""
    assert FromCenterAndCov().grammar_names == [
        "center_values",
        "cov",
        "lower_bounds",
        "upper_bounds",
    ]
