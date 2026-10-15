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
"""Utility functions for solver interaction."""
import datetime
import getpass
import json
import numpy as np
from numpy import array
from numpy import ndarray

# Python 2/3 compatibility
try:
    # unicode exists with Python 2 (Abaqus 2022 python) but not in Python 3 (VIMSEO)
    unicode
except NameError:
    # Python 3
    unicode = str


ARG_FILE = "job_arguments.json"
OUT_FILE = "job_outputs.json"


def import_json_inputs(json_input_file):
    """Base function importing job input parameters from a JSON file"""

    # TODO factorise this function wih load_job_arguments()

    with open(json_input_file, 'r') as input_file:
        inputs = json.loads(input_file.read())
        for k, v in inputs.items():
            if isinstance(v, unicode): 
                # unicode strings are casted into strings
                inputs[k] = str(v)
            if isinstance(v, (list, type(np.array([0.0])))):
                # np.array with only one element is unpacked into a scalar
                if len(v) == 1:
                    inputs[k] = v[0]
                    if isinstance(v[0], unicode):
                        # unicode strings are casted into strings
                        inputs[k] = str(v[0])
                elif len(v) == 0:
                    msg = "Error - empty input value for the following input key: "
                    raise ValueError(msg, k)

        return inputs


def write_json_dict(output_file, dict_outputs):
    """Dumps a dict of outputs (scalars and curves) into a local json file
    Args:
        output_file: name of the JSON file to dump the data into (e.g.
        "job_arguments.json")
        dict_outputs: dictionnary of data to be dumped into the json file
    """
    with open(output_file, 'w') as f:
        f.write(json.dumps(dict_outputs, indent=4))


def write_job_outputs_csv_exhaustive(odb_name, outputs, *legacy_args):
    """Write an exhaustive CSV output file based on an outputs dict, formated
    for human reading. Scalars and curves are split automatically based on
    their size, and the output file name is derived from ``odb_name``."""
    if legacy_args:
        msg = (
            "write_job_outputs_csv_exhaustive() now takes (odb_name, outputs) "
            "instead of (output_file, dict_scalars, dict_curves) -- update this caller."
        )
        raise TypeError(msg)

    dict_scalars = {}
    dict_curves = {}
    for key, value in outputs.items():
        if np.size(value) > 1:
            dict_curves[key] = value
        else:
            dict_scalars[key] = value

    output_file = 'output_' + odb_name[:-4] + '_' + time_stamper_formatted() + '.csv'
    with open(output_file, 'w') as f:
        f.write(get_metadata_txt())

        # Writing the scalars in the text file
        f.write("\n########################################################\n")
        for key, value in dict_scalars.items():
            value_format = "{0:.3f}".format(value) if isinstance(value, float) else value
            f.write(key + " = " + str(value_format) + "\n")

        # Writing the curves in the text file
        f.write("########################################################\n")
        for key in dict_curves:
            f.write(key + " ; ")
        f.write("\n")
        max_len = max(len(v) for k, v in dict_curves.items())
        for i in range(max_len):
            for key in dict_curves:
                if i < len(dict_curves[key]):
                    formated_text = "{0:.6f}".format(dict_curves[key][i])
                    f.write(formated_text)

                f.write(";")

            f.write("\n")
        f.close()


def local_slope_computation(
    x_curve,
    y_curve,
    x_min=None,
    x_max=None,
    y_min=None,
    y_max=None,
    method="regression",
):
    """Computes the slope (y over x) of the curve (x_curve;y_curve) in the segment [x_min;x_max] or [y_min;y_max].

    Args :
        x_curve: [list] vector of x_values
        y_curve: [list] vector of y values
        x_min: [float] initial value of the x-interval where to compute the slope
        x_max: [float] final   value of the x-interval where to compute the slope
        y_min: [float] initial value of the y-interval where to compute the slope
        y_max: [float] final   value of the y-interval where to compute the slope
        method:[str] "regression" or "average"
    Examples:
        >>> modulus_e005_e025 = local_slope_computation(
        ...     strain_history, stress_history, x_min=0.0005, x_max=0.0025, method="average"
        ... )
        >>> modulus_10_50 = local_slope_computation(
        ...     strain_history,
        ...     stress_history,
        ...     x_min=0.10 * strain_fail,
        ...     x_max=0.50 * strain_fail,
        ...     method="regression",
        ... )
    Returns:
        modulus: [float] the local computed slope
    """

    if x_min is not None and x_max is not None and y_min is None and y_max is None:
        z_curve, z_min, z_max = x_curve, x_min, x_max
    elif x_min is None and x_max is None and y_min is not None and y_max is not None:
        z_curve, z_min, z_max = y_curve, y_min, y_max
    else:
        # if not ((x_min is None and x_max is None) or (y_min is None and y_max is None)):
        msg = "Either (x_min and x_max) or (y_min and y_max) should not be None"
        raise ValueError(msg)

    if method == "regression":  # linear regression
        list_indexes = [
            i
            for i in range(len(z_curve))
            if abs(z_min) <= abs(z_curve[i]) <= abs(z_max)
        ]

        if len(list_indexes) < 2:
            return np.nan  # not enough point for linear regression

        # compute stiffness by linear regression
        x = [x_curve[j] for j in list_indexes]
        y = [y_curve[j] for j in list_indexes]

        x_ponderate = np.vstack([x, np.ones(len(x))]).T
        modulus, _c = np.linalg.lstsq(x_ponderate, y, rcond=-1)[0]

    elif method == "average":  # basic slope between two extreme points
        x_min_found, x_max_found, y_min_found, y_max_found = (
            np.nan,
            np.nan,
            np.nan,
            np.nan,
        )
        for i in range(len(z_curve)):
            if abs(z_curve[i]) >= abs(z_min):
                x_min_found = x_curve[i]
                y_min_found = y_curve[i]
                break
        for j in range(i + 1, len(z_curve)):
            x_max_found = x_curve[j]
            y_max_found = y_curve[j]
            if abs(z_curve[j]) >= abs(z_max):
                break

        modulus = (y_max_found - y_min_found) / (x_max_found - x_min_found)
    else:
        msg = "Unexpected value for resolution method: "
        raise ValueError(msg, method)

    return modulus


class EnhancedJSONEncoderModelWrapper(json.JSONEncoder):
    def default(self, o):
        import dataclasses

        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, ndarray):
            return o.tolist()
        return super().default(o)


def write_job_arguments_to_file(argument_file, data):
    """Write a json file containing the parameters for the external solver.

    ``data`` can contain Dataclasses and NumPy arrays.

    Args:
        argument_file: The path to the json file containing the arguments for the solver.
        data: A dictionary containing the parameters necessary for the Abaqus script.

    """
    with open(argument_file, "w") as f:
        json.dump(dict(data), f, cls=EnhancedJSONEncoderModelWrapper)


def load_job_arguments():
    """Load json file containing arguments for Abaqus.
    List are casted to Numpy arrays, and unicode strings are casted to strings."""

    arguments = json.load(open(ARG_FILE))
    for k, v in arguments.items():
        if isinstance(v, list):
            arguments[k] = array(v)
        if isinstance(v, unicode):  # noqa: F821
            arguments[k] = str(arguments[k])
    return arguments


def time_stamper_full_text():
    """Generate a string time stamp, meant for text prints."""
    return str(datetime.datetime.now())[0:19]


def time_stamper_formatted():
    """Generate a string time stamp, meant for suffixing folder names."""
    return time_stamper_full_text().replace(":", "-").replace(" ", "_")


def get_metadata_txt():
    """Generate metadata as string (time stamp + user)."""
    return (
        "## Generated the " + time_stamper_full_text() + "   by  " + getpass.getuser()
    )
