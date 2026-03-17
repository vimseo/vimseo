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
from copy import deepcopy
from typing import TYPE_CHECKING
from typing import ClassVar

from vimseo.core.base_integrated_model import IntegratedModel
from vimseo.core.components.component_factory import ComponentFactory
from vimseo.core.components.external_software_component import ExternalSoftwareComponent
from vimseo.core.components.subroutines.subroutine_wrapper_factory import (
    SubroutineWrapperFactory,
)
from vimseo.core.load_case_factory import LoadCaseFactory
from vimseo.core.model_settings import IntegratedModelSettings
from vimseo.material.material import Material

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vimseo.core.components.base_component import BaseComponent

LOGGER = logging.getLogger(__name__)


class PreRunPostModel(IntegratedModel):
    """A model chaining a pre-processor, a run-processor, and a post-processor.

    An ``PreRunPostModel`` contains three :class:`~.ExternalSoftwareComponent`:
    The model execution is basically the sequenced
    execution of these three chained components.

    The description of the components is done through the following class attributes:
    * ``PRE_PROC_FAMILY``
    * ``RUN_FAMILY``
    * ``POST_PROC_FAMILY``
    For instance, PRE_PROC_FAMILY = "PreStraightBeam" corresponds to the preprocessor
    family of the analytical beam model ``StraightBeamModel``.
    If this model is instantiated for the ``Cantilever`` load case, the model
    preprocessor class is ``PreStraightBeam_Cantilever`` according to the naming
    convention `{PRE_PROC_FAMILY}_{load_case}` (and similarly for the postprocessor).

    For FE models using a user subroutine, the list of subroutines used is defined
    in class attribute ``SUBROUTINE_NAMES``.
    """

    _pre_processor: BaseComponent
    _run_processor: BaseComponent
    _post_processor: BaseComponent

    PRE_PROC_FAMILY = None
    """The prefix of the pre-processor class name (typically ``MyPre`` for a pre-
    processor class named ``MyPre_MyLoadCase``)."""

    RUN_FAMILY = None
    """The prefix of the run-processor class name."""

    POST_PROC_FAMILY = None
    """The prefix of the post-processor class name."""

    SUBROUTINES_NAMES: ClassVar[Sequence[str]] = []
    """The names of the subroutines."""

    N_CPUS = 1
    """The default number of cpus used to run the model."""

    _INDEX_DISC_OUTPUT_TO_REMOVE: ClassVar[Sequence[int]] = [0, 1]

    def __init__(self, load_case_name: str, **options):

        options = IntegratedModelSettings(**options).model_dump()
        material = (
            Material.from_json(self.MATERIAL_FILE) if self.MATERIAL_FILE != "" else None
        )

        component_factory = ComponentFactory()

        run_processor = component_factory.create(
            self.RUN_FAMILY,
            material_grammar_file=self._MATERIAL_GRAMMAR_FILE,
            material=material,
            check_subprocess=options["check_subprocess"],
        )
        self._subroutine_names = deepcopy(self.SUBROUTINES_NAMES)
        for sub_name in self._subroutine_names:
            run_processor.subroutine_list.append(
                SubroutineWrapperFactory().create(sub_name)
            )

        load_case = LoadCaseFactory().create(
            load_case_name, domain=self._LOAD_CASE_DOMAIN
        )
        components = [
            component_factory.create(
                self.PRE_PROC_FAMILY,
                load_case=load_case,
                material_grammar_file=self._MATERIAL_GRAMMAR_FILE,
                material=material,
                check_subprocess=options["check_subprocess"],
            ),
            run_processor,
            component_factory.create(
                self.POST_PROC_FAMILY,
                load_case=load_case,
                check_subprocess=options["check_subprocess"],
            ),
        ]

        # # TODO update run grammar after super.init.
        # # run component has its grammar defined from pre and post components:
        # components[1].input_grammar = deepcopy(components[0].output_grammar)
        # # TODO is it neccesary? Should be done explicitly by the user instead.
        # components[1].input_grammar.update(components[0].input_grammar)
        # components[1].output_grammar = deepcopy(components[2].input_grammar)
        # components[1].output_grammar.update_from_data({"error_code": atleast_1d(0)})
        # components[1].output_grammar.required_names.add("error_code")

        super().__init__(load_case_name, components, **options)

        # TODO automatically add material grammar to run component input grammar.

        self._pre_processor = self._chain.disciplines[0]
        self._run_processor = self._chain.disciplines[1]
        self._post_processor = self._chain.disciplines[2]

        self._component_with_jacobian = self.run
        self._set_differentiated_names(self.run)

        if isinstance(self.run, ExternalSoftwareComponent):
            self.run.job_executor._user_job_options.update({"n_cpus": self.N_CPUS})

    @property
    def run(self) -> BaseComponent:
        """The component running the external software."""
        return self._run_processor

    @property
    def n_cpus(self):
        """The number of CPUs to run this model."""
        return self.run.n_cpus

    def set_n_cpus(self, n_cpus: int):
        LOGGER.warning(
            "This method is deprecated, "
            "please use ``model.run.job_executor.set_options()."
        )

    def get_dataflow(self):
        """The inputs and outputs of the components of the model.

        Returns:
             A dictionary mapping component name to its input and output names.
        """

        dataflow = super().get_dataflow()
        dataflow["subroutine_names"] = self._subroutine_names

        return dataflow
