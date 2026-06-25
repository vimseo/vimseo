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

# from __future__ import annotations
#
# from typing import Iterable
#
# from gemseo.uncertainty.sensitivity.analysis import SensitivityAnalysis
# from gemseo.uncertainty.sensitivity.morris.oat import _OATSensitivity
# from numpy import array
#
# from vimseo.tools.space.space_tool import SpaceTool
#
#
# class OATAnalysis(SensitivityAnalysis):
#     """Add-on for GEMSEO to be able to compute sensitivity indices from simple "One-at-a-
#     time" method.
#
#     Two OAT indices are defined:
#     - absolute variation of the outputs ("delta_f")
#     - relative variation of the outputs ("relative_delta_f")
#
#     Variation of inputs are defined either:
#     - from the range of parameter values as defined in a parameter space, multiplied
#     by the coefficient of variation (CoV) - or from a central point multiplied
#     by the CoV
#     """
#
#     DEFAULT_DRIVER = "CustomDOE"
#
#     # disciplines: Collection[MDODiscipline],
#     # parameter_space: ParameterSpace,
#     # n_samples: int | None,
#     # output_names: Iterable[str] | None = None,
#     # algo: str | None = None,
#     # algo_options: Mapping[str, DOELibraryOptionType] | None = None,
#     # n_replicates: int = 5,
#     # step: float = 0.05,
#     # formulation: str = "MDF",
#     # ** formulation_options: Any,
#     def __init__(
#         self,
#         disciplines,
#         parameter_space=None,  # type:gemseo.algos.design_space.DesignSpace
#         n_samples=1,
#         output_names: Iterable[str] | None = None,
#         algo=None,
#         algo_options=None,
#         n_replicates: int = 5,
#         step: float = 0.05,
#         formulation: str = "MDF",
#         input_data=None,  # type: dict
#         cov=0.05,  # type: float
#     ):  # type: (...) -> None
#         self.delta_f = None
#         self.relative_delta_f = None
#
#         if not parameter_space:
#             parameter_space = self.build_parameter_space(input_data, 2 * cov)
#             step = 1 / 4.0
#         else:
#             step = cov
#
#         self.__oat_discipline = _OATSensitivity(disciplines, parameter_space, step)
#
#         if not input_data:
#             input_data = {
#                 var: array(
#                     [
#                         0.5
#                         * (
#                             parameter_space.get_upper_bound(var)[0]
#                             + parameter_space.get_lower_bound(var)[0]
#                         )
#                     ]
#                 )
#                 for var in parameter_space.variable_names
#             }
#
#         samples = array(
#             [[input_data[var][0] for var in parameter_space.variable_names]]
#         )
#         n_samples = 1
#         super().__init__(
#             discipline=self.__oat_discipline,
#             parameter_space=parameter_space,
#             n_samples=n_samples,
#             algo=self.DEFAULT_DRIVER,
#             algo_options={"samples": samples},
#         )
#
#         self._main_method = "OAT(df)"
#         self.default_output = list(disciplines.output_grammar.names)
#
#     @staticmethod
#     def build_parameter_space(input_data, delta):
#         """Build a parameter space with uniform distribution and lower and upper bounds
#         defined by +/- delta*mean_value."""
#         space_tool = SpaceTool()
#         space_tool.update(
#             space_builder="FromCenterAndCov",
#             distribution="OTUniformDistribution",
#             center_values=input_data,
#             cov=delta,
#         )
#         return space_tool.execute()
#
#     def output_value(self, output_name):  # type: (...) -> Dict[str, List[float]]
#         """The central value of the output."""
#         out_range = self.__oat_discipline.output_range
#         return out_range[output_name][0]
#
#     def compute_indices(
#         self,
#         outputs=None,  # type: Optional[Sequence[str]]
#         normalize=True,  # type: Optional[Boolean]
#     ):  # type: (...) -> Dict[str,IndicesType]
#         """
#
#         :param outputs:
#         :param normalize: normalize with the central value of the outputs
#         :return:
#         """
#
#         output_names = outputs or self.default_output
#
#         if not isinstance(output_names, list):
#             output_names = [output_names]
#
#         self.delta_f = {name: {} for name in output_names}
#         self.relative_delta_f = {name: {} for name in output_names}
#
#         for out_name in output_names:
#             for in_name in self.inputs_names:
#                 fd_name = self.__oat_discipline.get_fd_name(in_name, out_name)
#
#                 self.delta_f[out_name][in_name] = self.__oat_discipline.io.data[fd_name]
#                 self.relative_delta_f[out_name][in_name] = self.delta_f[out_name][
#                     in_name
#                 ] / self.output_value(out_name)
#
#         return self.indices
#
#     @property
#     def main_indices(self):  # type: (...) -> IndicesType
#         return self.delta_f
#
#     @property
#     def indices(self):  # type: (...) -> Dict[str,IndicesType]
#         return {"delta_f": self.delta_f, "relative_delta_f": self.relative_delta_f}
#
#     def plot(
#         self,
#         output,  # type: Union[str,Tuple[str,int]]
#         inputs=None,  # type: Optional[Iterable[str]]
#         title=None,  # type: Optional[str]
#         save=True,  # type: bool
#         show=False,  # type: bool
#         directory_path=None,  # type: Optional[str]
#         file_name=None,  # type: Optional[str]
#         file_path=None,  # type: Optional[Union[str,Path]]
#         file_format=None,  # type: Optional[str]
#     ):  # type: (...) -> None
#         """Plot the sensitivity indices."""
#
#         self.plot_bar(
#             outputs=output,
#             inputs=inputs,
#             standardize=False,
#             title=title,
#             save=save,
#             show=show,
#             file_path=file_path,
#             directory_path=directory_path,
#             file_name=file_name,
#             file_format=file_format,
#         )
from __future__ import annotations
