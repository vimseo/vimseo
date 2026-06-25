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

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemseo.mlearning.regression.regression import MLRegressionAlgo


class AlgoWrapperForSklearn:
    """A class to wrap Gemseo's regression algorithms for usage by Sklearn
    cross_val_predict method. This method require a wrapper with following methods.

    implemented:
    - fit(x, y): the method to fit the algorithm to the data x, y.
    - predict(x): the method to predict the response for x.
    - get_params(deep): a getter to the current parameters.
    - set_params(**parameters): a setter for the parameters of the algo.
    In addition, the parameters have to be defined as attributes of the wrapper.
    """

    def __init__(self, algo: MLRegressionAlgo, **parameters) -> None:
        self.algo = algo
        self.algo.parameters.update(parameters)
        self._set_wrapper_params(parameters)

    def fit(self, x, y):
        return self.algo._fit(x, y)

    def predict(self, x):
        return self.algo.predict(x)

    def get_params(self, deep=True):
        parameters = deepcopy(self.algo.parameters)
        parameters.update({"algo": self.algo})
        return parameters

    def _set_wrapper_params(self, parameters):
        for parameter, value in parameters.items():
            setattr(self, parameter, value)

    def set_params(self, **parameters):
        data = deepcopy(self.algo.learning_set)
        transformer = deepcopy(self.algo.transformer)
        input_names = deepcopy(self.algo.input_names)
        output_names = deepcopy(self.algo.output_names)

        self._set_wrapper_params(parameters)

        self.algo = self.algo.__class__(
            data=data,
            transformer=transformer,
            input_names=input_names,
            output_names=output_names,
            **parameters,
        )

        return self
